import os
import time
from app.core.logger import logger
from faster_whisper import WhisperModel

class TranscriptionService:
    def __init__(self, model_name: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """
        Loads the faster-whisper model.
        For CPU, compute_type is typically 'int8' to minimize RAM/CPU usage and maximize speed.
        """
        logger.info(f"Loading Whisper model '{model_name}' on {device} (compute_type={compute_type})...")
        start_time = time.time()
        
        # Download and instantiate the WhisperModel
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        
        logger.info(f"Whisper model loaded successfully in {time.time() - start_time:.2f}s.")

    def transcribe_audio(self, file_path: str, language: str | None = None) -> dict:
        """
        Transcribes the audio file located at file_path.
        Returns a dict containing text, detected language, and segments metadata.
        Handles corrupt or empty files gracefully.

        Args:
            file_path: Path to the audio file.
            language:  Optional ISO-639-1 language code (e.g. 'hi', 'en', 'fr').
                       When provided, Whisper is forced into that language so it
                       produces native-script output (e.g. Devanagari for Hindi)
                       instead of auto-detecting or transliterating.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        logger.info(f"Starting ASR transcription for: {file_path}" +
                    (f" [forced language={language}]" if language else ""))
        start_time = time.time()

        try:
            # Check if file is empty (0 size)
            if os.path.getsize(file_path) == 0:
                logger.warning(f"Audio file is empty (0 bytes): {file_path}")
                return {
                    "text": "",
                    "language": "unknown",
                    "language_probability": 0.0,
                    "segments": [],
                    "latency_sec": round(time.time() - start_time, 3)
                }

            # Run transcription using faster-whisper.
            # beam_size=1 (greedy decoding) is 2.5-3x faster on shared CPU with virtually identical accuracy.
            # vad_filter=True removes silence blocks before running neural ASR.
            transcribe_kwargs: dict = {
                "beam_size": 1,
                "best_of": 1,
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=500),
            }
            if language:
                transcribe_kwargs["language"] = language
            segments, info = self.model.transcribe(file_path, **transcribe_kwargs)

            # Consume the segments generator to run inference
            segments_list = []
            text_chunks = []
            
            for segment in segments:
                text_chunks.append(segment.text)
                segments_list.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(segment.avg_logprob, 4)
                })

            transcribed_text = "".join(text_chunks).strip()
            latency = time.time() - start_time
            logger.info(f"Transcription complete in {latency:.2f}s. Detected language: '{info.language}' (prob={info.language_probability:.2f})")

            return {
                "text": transcribed_text,
                "language": info.language,
                "language_probability": round(info.language_probability, 4),
                "segments": segments_list,
                "latency_sec": round(latency, 3)
            }

        except Exception as e:
            logger.error(f"ASR transcription failed: {e}", exc_info=True)
            # Raise exception so calling endpoints/handlers can return appropriate error codes
            raise RuntimeError(f"ASR transcription error: {str(e)}")
