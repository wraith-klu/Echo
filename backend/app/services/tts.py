"""
TTSService: Local neural Text-to-Speech service using Piper TTS.

Provides high-quality, local speech synthesis for 10 target languages.
Downloads and caches models from the rhasspy/piper-voices HF repo.
Ensures outputs are normalized to standard 16-bit, 16kHz mono PCM WAV
for optimal streaming/I2S playback on ESP32 + MAX98357A.
"""
import os
import time
import urllib.request
import io
import wave
from pydub import AudioSegment
from piper import PiperVoice

from app.core.logger import logger

# Base Hugging Face repository URL for downloading voices
PIPER_VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# Cache directory for storing model files (.onnx and .onnx.json)
CACHE_DIR = os.path.expanduser("~/.cache/piper")

# Language code to Piper model relative path mapping
# Quality 'medium' generally uses 22.05kHz, which we will downsample to 16kHz.
PIPER_MODEL_MAP = {
    "en": "en/en_US/lessac/medium/en_US-lessac-medium.onnx",
    "hi": "hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx",       # Hindi
    "es": "es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
    "fr": "fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
    "de": "de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
    "it": "it/it_IT/paola/medium/it_IT-paola-medium.onnx",
    "pt": "pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
    "zh": "zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
    "ja": "ja/ja_JP/hi_fi_captain/medium/ja_JP-hi_fi_captain-medium.onnx",
    "ko": "ko/ko_KR/kss/medium/ko_KR-kss-medium.onnx",
    "ru": "ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx",
    "ar": "ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx",   # Arabic
}


class TTSService:
    """
    Service to manage loading, caching, and inference of Piper voice models.
    Loaded voices are cached in memory for zero-latency subsequent triggers.
    """

    def __init__(self):
        # Dictionary to hold loaded PiperVoice instances (lazy loading)
        self.loaded_voices = {}
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"Initialized TTSService with cache directory: {CACHE_DIR}")

    def _get_model_paths(self, lang: str) -> tuple[str, str]:
        """Get local absolute paths for the ONNX model and JSON config."""
        relative_path = PIPER_MODEL_MAP[lang]
        onnx_filename = os.path.basename(relative_path)
        json_filename = onnx_filename + ".json"

        onnx_path = os.path.join(CACHE_DIR, onnx_filename)
        json_path = os.path.join(CACHE_DIR, json_filename)
        return onnx_path, json_path

    def _download_file(self, url: str, local_path: str):
        """Download a file with basic retry logic."""
        logger.info(f"Downloading {url} -> {local_path} ...")
        t0 = time.time()
        
        # Download to a temporary file first to avoid corruption on crash
        temp_path = local_path + ".tmp"
        
        # Disable proxy or use standard User-Agent to prevent 403s
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=180) as response, open(temp_path, "wb") as out_file:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    out_file.write(chunk)
            
            # Atomic rename
            if os.path.exists(local_path):
                os.remove(local_path)
            os.rename(temp_path, local_path)
            logger.info(f"Finished download in {time.time() - t0:.2f}s")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Download failed for {url}: {e}", exc_info=True)
            raise e

    def _ensure_model_downloaded(self, lang: str) -> tuple[str, str]:
        """Download the .onnx and .onnx.json files if they do not exist locally."""
        onnx_path, json_path = self._get_model_paths(lang)
        relative_path = PIPER_MODEL_MAP[lang]

        # Download ONNX model if missing
        if not os.path.exists(onnx_path) or os.path.getsize(onnx_path) == 0:
            onnx_url = f"{PIPER_VOICES_URL}/{relative_path}"
            self._download_file(onnx_url, onnx_path)

        # Download JSON config if missing
        if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
            json_url = f"{PIPER_VOICES_URL}/{relative_path}.json"
            self._download_file(json_url, json_path)

        return onnx_path, json_path

    def load_voice(self, lang: str) -> PiperVoice:
        """Load a PiperVoice model instance for the target language (thread-safe cache)."""
        if lang in self.loaded_voices:
            return self.loaded_voices[lang]

        logger.info(f"Loading Piper voice for language '{lang}' ...")
        t0 = time.time()
        
        onnx_path, _ = self._ensure_model_downloaded(lang)
        
        # Load the voice model into memory
        # piper.PiperVoice.load handles parsing the JSON config at config_path = model_path + ".json"
        voice = PiperVoice.load(onnx_path)
        
        self.loaded_voices[lang] = voice
        logger.info(f"Loaded Piper voice '{lang}' in {time.time() - t0:.2f}s")
        return voice

    def synthesize_speech(self, text: str, target_lang: str) -> bytes:
        """
        Synthesize text into speech WAV bytes, normalized to 16kHz, mono, 16-bit PCM.

        Args:
            text:        The text to synthesize.
            target_lang: ISO 639-1 language code (e.g. "en", "es").

        Returns:
            bytes: Normalized WAV file bytes.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("TTS input text is empty.")

        lang_code = target_lang.lower().strip()
        if lang_code not in PIPER_MODEL_MAP:
            raise ValueError(
                f"Unsupported TTS language '{target_lang}'. "
                f"Supported: {sorted(PIPER_MODEL_MAP.keys())}"
            )

        t0 = time.time()

        # 1. Retrieve the Piper voice model
        voice = self.load_voice(lang_code)

        # 2. Synthesize to raw audio using a memory buffer
        logger.info(f"Synthesizing '{lang_code}' speech: \"{clean_text[:60]}...\"")
        wav_buf = io.BytesIO()
        
        # Synthesize WAV bytes directly into the buffer
        try:
            with wave.open(wav_buf, "wb") as wav_file:
                # Pre-set channels/framerate so if phonemization fails, wave.close() won't mask it with '# channels not specified'
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                sample_rate = getattr(getattr(voice, "config", None), "sample_rate", 22050)
                wav_file.setframerate(sample_rate)
                voice.synthesize_wav(clean_text, wav_file)
        except Exception as synth_err:
            real_err = synth_err.__context__ or synth_err
            logger.error(f"TTS synthesis failed for '{lang_code}': {real_err}", exc_info=True)
            raise real_err
        
        raw_wav_bytes = wav_buf.getvalue()
        raw_latency = time.time() - t0

        # 3. Audio format conversion (Normalization)
        # Piper models generate either 16000Hz or 22050Hz WAV audio.
        # We enforce exactly 16000Hz, mono, 16-bit depth (2 bytes per sample) for I2S.
        t_conv = time.time()
        try:
            audio: AudioSegment = AudioSegment.from_file(io.BytesIO(raw_wav_bytes), format="wav")  # type: ignore[assignment]
            
            # Apply formatting if it doesn't match
            if audio.frame_rate != 16000 or audio.channels != 1 or audio.sample_width != 2:
                logger.info(
                    f"Converting audio from {audio.frame_rate}Hz/{audio.channels}ch/{audio.sample_width*8}bit "
                    "-> 16000Hz/1ch/16bit..."
                )
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # type: ignore[attr-defined]
                
            out_buf = io.BytesIO()
            audio.export(out_buf, format="wav")  # type: ignore[attr-defined]
            final_wav_bytes = out_buf.getvalue()
        except Exception as conv_err:
            logger.warning(f"Audio conversion failed: {conv_err}. Returning raw Piper WAV.", exc_info=True)
            final_wav_bytes = raw_wav_bytes

        total_latency = time.time() - t0
        logger.info(
            f"TTS synthesis complete. Raw latency: {raw_latency:.2f}s | "
            f"Total: {total_latency:.2f}s | Size: {len(final_wav_bytes)} bytes"
        )
        
        return final_wav_bytes
