import os
import json
import soundfile as sf
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.services.ingestion import AudioIngestionService
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES
from app.services.translation import NLLB_LANG_MAP

router = APIRouter()

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech translation (backward compatibility).
    """
    await websocket.accept()
    logger.info("WebSocket connection established with client on legacy stream.")
    try:
        while True:
            data = await websocket.receive_bytes()
            logger.info(f"Received audio chunk of size: {len(data)} bytes")
            await websocket.send_json({
                "transcription": "Hello (placeholder)",
                "translation": "Hola (placeholder)",
                "is_final": False
            })
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client on legacy stream.")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()


@router.websocket("/audio")
async def websocket_audio_endpoint(
    websocket: WebSocket,
    device_id: str = "ESP32_Device",
    source_language: str = None,
    target_language: str = None
):
    """
    WebSocket endpoint for receiving real-time audio chunk streams from IoT/ESP32 devices.
    
    Query parameters:
    - device_id: Unique identifier for the client device (e.g. ESP32_Device).
    - source_language: Optional manual override language code (e.g. 'en', 'es').
    
    Accepts:
    - Binary message containing raw PCM audio (16-bit, 16kHz, mono).
    - Text message containing JSON commands like {"command": "set_source_language", "language": "es"}
      or raw command string like "end_of_speech".
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established with device ID: '{device_id}'")
    
    # Session state variables
    active_source_language = None
    active_target_language = None

    if source_language:
        lang_clean = source_language.strip().lower()
        if LanguageDetectionService.is_language_supported(lang_clean):
            active_source_language = lang_clean
            logger.info(f"WebSocket session initialized with query parameter source_language override: '{active_source_language}'")
        else:
            logger.warning(f"Unsupported query parameter source_language: '{source_language}'. Defaulting to auto-detection.")
            await websocket.send_json({
                "status": "warning",
                "message": f"Unsupported source language override '{source_language}'. Defaulting to auto-detection."
            })

    if target_language:
        tgt_clean = target_language.strip().lower()
        if tgt_clean in NLLB_LANG_MAP:
            active_target_language = tgt_clean
            logger.info(f"WebSocket session initialized with query parameter target_language: '{active_target_language}'")
        else:
            logger.warning(f"Unsupported query parameter target_language: '{target_language}'. Translation disabled.")
            await websocket.send_json({
                "status": "warning",
                "message": f"Unsupported target language '{target_language}'. Translation disabled."
            })
            
    # Isolated ingestion service instance for this specific session
    ingestion_service = AudioIngestionService()
    
    async def process_and_respond(file_path: str, duration: float, trigger_reason: str):
        from app.main import ml_models
        from app.services.pipeline import PipelineOrchestrator
        
        try:
            # Run end-to-end translation pipeline orchestrator
            result = await PipelineOrchestrator.run(
                file_path=file_path,
                ml_models=ml_models,
                device_id=device_id,
                source_language_override=active_source_language,
                target_language=active_target_language
            )
            
            # Prepare metadata payload for client (e.g. ESP32 display)
            audio_follows = False
            audio_size_bytes = 0
            
            if result.tts and "file_path" in result.tts:
                audio_follows = True
                audio_size_bytes = result.tts.get("audio_size_bytes", 0)
                
            response_payload = {
                "status": result.status,
                "filename": result.filename,
                "duration": result.duration,
                "message": f"Speech boundary detected by {trigger_reason}. {result.message}",
                "transcription": result.transcription,
                "translation": result.translation,
                "latencies": result.latencies,
                "audio_follows": audio_follows,
                "audio_size_bytes": audio_size_bytes
            }
            
            if result.error:
                response_payload["error"] = result.error
                
            # Frame 1: Send JSON metadata text frame
            await websocket.send_json(response_payload)
            
            # Frame 2: Send binary WAV audio frame if TTS was synthesized
            if audio_follows:
                tts_file_path = result.tts["file_path"]
                try:
                    with open(tts_file_path, "rb") as f:
                        wav_bytes = f.read()
                    await websocket.send_bytes(wav_bytes)
                    logger.info(f"Streamed {len(wav_bytes)} bytes of synthesized audio WAV back to client {device_id}")
                except Exception as file_err:
                    logger.error(f"Failed to read and send synthesized audio file: {file_err}")
                    
        except Exception as err:
            logger.error(f"Pipeline process and respond failed on WebSocket: {err}", exc_info=True)
            await websocket.send_json({
                "status": "error",
                "message": f"Pipeline processing failed: {str(err)}",
                "filename": os.path.basename(file_path)
            })

    try:
        while True:
            # Receive incoming frames (either binary or text)
            message = await websocket.receive()
            
            # Handle binary audio frame
            if "bytes" in message:
                data = message["bytes"]
                if not data:
                    continue
                
                # Append audio to the buffer and run silence energy checks (VAD)
                ingestion_service.add_chunk(data)
                
                # If silence duration threshold is reached, save the segment
                if ingestion_service.has_speech_ended():
                    duration = ingestion_service.get_duration()
                    if duration > 0.1: # Only save if we actually have some speech
                        file_path = ingestion_service.save_buffer_to_wav(device_id)
                        if file_path:
                            await process_and_respond(file_path, duration, "VAD")
                    else:
                        ingestion_service.clear()
            
            # Handle text commands (e.g., explicit end of speech signals or overrides)
            elif "text" in message:
                text_data = message["text"]
                logger.info(f"Received text message from device {device_id}: {text_data}")
                
                # Check if it is a JSON command
                is_command = False
                try:
                    command_data = json.loads(text_data)
                    if isinstance(command_data, dict):
                        cmd = command_data.get("command")
                        
                        if cmd == "set_source_language":
                            is_command = True
                            lang = command_data.get("language")
                            if lang:
                                lang_clean = lang.strip().lower()
                                if LanguageDetectionService.is_language_supported(lang_clean):
                                    active_source_language = lang_clean
                                    logger.info(f"WebSocket session override set to: '{active_source_language}'")
                                    await websocket.send_json({
                                        "status": "success",
                                        "message": f"Source language set to '{active_source_language}'"
                                    })
                                else:
                                    logger.warning(f"Unsupported source language override requested: '{lang}'")
                                    await websocket.send_json({
                                        "status": "error",
                                        "message": f"Unsupported source language '{lang}'. Supported: {sorted(list(SUPPORTED_LANGUAGES))}"
                                    })
                                    
                        elif cmd == "clear_source_language":
                            is_command = True
                            active_source_language = None
                            logger.info("WebSocket session source_language override cleared.")
                            await websocket.send_json({
                                "status": "success",
                                "message": "Source language override cleared. Auto-detection enabled."
                            })

                        elif cmd == "set_target_language":
                            is_command = True
                            lang = command_data.get("language")
                            if lang:
                                tgt_clean = lang.strip().lower()
                                if tgt_clean in NLLB_LANG_MAP:
                                    active_target_language = tgt_clean
                                    logger.info(f"WebSocket session target_language set to: '{active_target_language}'")
                                    await websocket.send_json({
                                        "status": "success",
                                        "message": f"Target language set to '{active_target_language}'. Translation enabled."
                                    })
                                else:
                                    logger.warning(f"Unsupported target language requested: '{lang}'")
                                    await websocket.send_json({
                                        "status": "error",
                                        "message": f"Unsupported target language '{lang}'. Supported: {sorted(NLLB_LANG_MAP.keys())}"
                                    })

                        elif cmd == "clear_target_language":
                            is_command = True
                            active_target_language = None
                            logger.info("WebSocket session target_language cleared. Translation disabled.")
                            await websocket.send_json({
                                "status": "success",
                                "message": "Target language cleared. Translation disabled."
                            })
                            
                        elif cmd == "end_of_speech":
                            # Treat JSON end_of_speech command the same as raw string command
                            pass
                except json.JSONDecodeError:
                    pass

                # If it wasn't handled as a configuration command, check for explicit end of speech
                if not is_command and "end_of_speech" in text_data:
                    duration = ingestion_service.get_duration()
                    if duration > 0.1:
                        file_path = ingestion_service.save_buffer_to_wav(device_id)
                        if file_path:
                            await process_and_respond(file_path, duration, "explicit command")
                    else:
                        await websocket.send_json({
                            "status": "warning",
                            "message": "Audio buffer is empty. Nothing to save."
                        })
                        ingestion_service.clear()

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection disconnected for device: {device_id}")
        # Save any leftover speech in buffer so we don't lose it
        duration = ingestion_service.get_duration()
        if duration > 0.3:
            file_path = ingestion_service.save_buffer_to_wav(device_id)
            logger.info(f"Saved remaining audio from disconnecting device: {file_path}")
            # Transcribe and log remaining audio offline
            from app.main import ml_models
            asr_service = ml_models.get("asr")
            if asr_service and file_path:
                try:
                    # Run offline transcription + LID logging
                    asr_res = asr_service.transcribe_audio(file_path)
                    lid_res = LanguageDetectionService.detect_language(
                        text=asr_res["text"],
                        whisper_lang=asr_res["language"],
                        whisper_prob=asr_res["language_probability"]
                    )
                    logger.info(f"Offline LID for remaining audio: {lid_res}")
                except Exception as asr_err:
                    logger.error(f"ASR failed on disconnect-saved audio: {asr_err}")
        else:
            ingestion_service.clear()

    except Exception as e:
        logger.error(f"Error on WebSocket connection for device {device_id}: {e}", exc_info=True)
        # Attempt to save buffer before closing if it contains speech
        try:
            if ingestion_service.get_duration() > 0.3:
                ingestion_service.save_buffer_to_wav(device_id)
        except Exception as save_err:
            logger.error(f"Failed to save buffer on crash: {save_err}")
        
        try:
            await websocket.close()
        except Exception:
            pass
