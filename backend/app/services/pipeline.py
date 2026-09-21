import os
import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict

from app.core.logger import logger
from app.services.language_detection import LanguageDetectionService
from app.services.translation import NLLB_LANG_MAP  # alias for LANG_NAME_MAP

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class PipelineResult:
    status: str  # "success", "partial_success", "error"
    filename: str
    duration: float
    message: str
    transcription: Optional[Dict[str, Any]] = None
    translation: Optional[Dict[str, Any]] = None
    tts: Optional[Dict[str, Any]] = None
    latencies: Optional[Dict[str, float]] = None
    error: Optional[str] = None

class PipelineOrchestrator:
    """
    Orchestrates the entire real-time translation pipeline:
    ASR -> Language Detection (LID) -> Machine Translation (MT) -> Text-to-Speech (TTS)
    
    Includes detailed latency tracking and robust error isolation.
    """
    
    @staticmethod
    async def run(
        file_path: str,
        ml_models: Dict[str, Any],
        device_id: str = "ESP32_Device",
        source_language_override: Optional[str] = None,
        target_language: Optional[str] = None,
        db: Optional["AsyncSession"] = None,
        session_id: Optional[str] = None,
    ) -> PipelineResult:
        t_start = time.time()
        latencies = {
            "ingestion_sec": 0.0,
            "asr_sec": 0.0,
            "lid_sec": 0.0,
            "translation_sec": 0.0,
            "tts_sec": 0.0,
            "total_sec": 0.0
        }
        
        filename = os.path.basename(file_path)
        duration = 0.0
        
        # 1. Retrieve Models from state
        asr_service = ml_models.get("asr")
        translation_service = ml_models.get("translation")
        tts_service = ml_models.get("tts")
        
        # Determine duration of source audio
        try:
            import soundfile as sf
            info = sf.info(file_path)
            duration = info.duration
        except Exception as e:
            logger.warning(f"Could not read audio file duration: {e}")
        
        if not asr_service:
            err_msg = "ASR service is not initialized."
            logger.error(err_msg)
            return PipelineResult(
                status="error",
                filename=filename,
                duration=duration,
                message=err_msg,
                error=err_msg,
                latencies=latencies
            )
            
        # 2. Run ASR transcription
        t0 = time.time()
        try:
            asr_res = asr_service.transcribe_audio(
                file_path,
                language=source_language_override.lower().strip() if source_language_override else None
            )
            latencies["asr_sec"] = round(time.time() - t0, 4)
        except Exception as asr_err:
            err_msg = f"ASR transcription failed: {asr_err}"
            logger.error(err_msg, exc_info=True)
            latencies["asr_sec"] = round(time.time() - t0, 4)
            return PipelineResult(
                status="error",
                filename=filename,
                duration=duration,
                message="ASR transcription failed.",
                error=err_msg,
                latencies=latencies
            )
            
        transcribed_text = asr_res.get("text", "").strip()
        
        # 3. Determine source language via LID (or override)
        t0 = time.time()
        if source_language_override:
            source_lang = source_language_override.lower().strip()
            lid_res = {
                "detected_language": source_lang,
                "confidence": 1.0,
                "source": "override"
            }
        else:
            lid_res = LanguageDetectionService.detect_language(
                text=transcribed_text,
                whisper_lang=asr_res.get("language"),
                whisper_prob=asr_res.get("language_probability", 0.0)
            )
        latencies["lid_sec"] = round(time.time() - t0, 4)
        
        source_lang = lid_res["detected_language"]
        is_source_supported = LanguageDetectionService.is_language_supported(source_lang)
        
        transcription_payload = {
            "text": transcribed_text,
            "segments": asr_res.get("segments", []),
            "latency_sec": asr_res.get("latency_sec", 0.0),
            "language_detection": lid_res,
            "supported": is_source_supported
        }
        
        # If ASR returned nothing or detected language is not supported, abort early with success but empty
        if not transcribed_text:
            latencies["total_sec"] = round(time.time() - t_start, 4)
            return PipelineResult(
                status="success",
                filename=filename,
                duration=duration,
                message="Audio segment processed. No speech detected.",
                transcription=transcription_payload,
                latencies=latencies
            )
            
        if not is_source_supported:
            latencies["total_sec"] = round(time.time() - t_start, 4)
            return PipelineResult(
                status="partial_success",
                filename=filename,
                duration=duration,
                message=f"Detected language '{source_lang}' is not supported.",
                transcription=transcription_payload,
                latencies=latencies
            )
            
        # 4. Run Machine Translation if target language is requested
        translation_payload = None
        target_lang = target_language.lower().strip() if target_language else None
        
        if target_lang and target_lang in NLLB_LANG_MAP:
            t0 = time.time()
            if not translation_service:
                translation_payload = {"error": "Translation service is not initialized."}
                logger.warning("Translation requested but TranslationService is not available.")
            else:
                try:
                    translation_payload = translation_service.translate_text(
                        text=transcribed_text,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                except Exception as t_err:
                    err_msg = f"Translation failed: {t_err}"
                    logger.warning(err_msg)
                    translation_payload = {"error": err_msg}
            latencies["translation_sec"] = round(time.time() - t0, 4)
            
        # 5. Run Text-to-Speech (TTS) if translation succeeded
        tts_payload = None
        translated_text = translation_payload.get("translated_text") if translation_payload else None
        
        if target_lang and translated_text:
            t0 = time.time()
            if not tts_service:
                tts_payload = {"error": "TTS service is not initialized."}
                logger.warning("TTS requested but TTSService is not available.")
            else:
                try:
                    from app.services.tts import PIPER_MODEL_MAP
                    if target_lang not in PIPER_MODEL_MAP:
                        tts_payload = {"error": f"Language '{target_lang}' is not supported by TTS."}
                    else:
                        tts_audio = tts_service.synthesize_speech(
                            text=translated_text,
                            target_lang=target_lang
                        )
                        
                        # Save the audio file
                        from app.services.ingestion import UPLOAD_DIR
                        os.makedirs(UPLOAD_DIR, exist_ok=True)
                        ts = int(time.time())
                        tts_filename = f"tts_{device_id}_{ts}_{target_lang}.wav"
                        tts_file_path = os.path.join(UPLOAD_DIR, tts_filename)
                        
                        with open(tts_file_path, "wb") as f:
                            f.write(tts_audio)
                            
                        tts_payload = {
                            "filename": tts_filename,
                            "file_path": tts_file_path,
                            "sample_rate": 16000,
                            "channels": 1,
                            "bit_depth": 16,
                            "audio_size_bytes": len(tts_audio)
                        }
                except Exception as tts_err:
                    err_msg = f"TTS synthesis failed: {tts_err}"
                    logger.error(err_msg, exc_info=True)
                    tts_payload = {"error": err_msg}
            latencies["tts_sec"] = round(time.time() - t0, 4)
            
        latencies["total_sec"] = round(time.time() - t_start, 4)
        
        # Log the pipeline latency breakdown
        logger.info(
            f"End-to-End Pipeline Completed for {filename} | "
            f"Total: {latencies['total_sec']:.2f}s | "
            f"Breakdown: ASR={latencies['asr_sec']:.2f}s, LID={latencies['lid_sec']:.2f}s, "
            f"Translation={latencies['translation_sec']:.2f}s, TTS={latencies['tts_sec']:.2f}s"
        )
        
        # Decide status
        status = "success"
        message = "Pipeline completed successfully."
        if (translation_payload and "error" in translation_payload) or (tts_payload and "error" in tts_payload):
            status = "partial_success"
            message = "Pipeline completed with some errors in translation/TTS stages."
            
        result = PipelineResult(
            status=status,
            filename=filename,
            duration=duration,
            message=message,
            transcription=transcription_payload,
            translation=translation_payload,
            tts=tts_payload,
            latencies=latencies
        )

        # Persist to database if a session was provided
        if db is not None:
            try:
                from app.services.db_service import log_translation, register_device
                await register_device(db, device_id=device_id)
                await log_translation(db, device_id=device_id, pipeline_result=result, session_id=session_id)
            except Exception as db_err:
                logger.warning(f"[DB] Failed to persist translation log: {db_err}")

        return result
