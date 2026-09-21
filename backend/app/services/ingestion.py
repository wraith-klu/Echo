import os
import time
import numpy as np
import soundfile as sf
from app.core.logger import logger

# Directory to save audio uploads
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_uploads"))

class AudioIngestionService:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        bit_depth: int = 16,
        rms_threshold: float = 500.0,
        silence_timeout_sec: float = 1.5,
        max_duration_sec: float = 15.0
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bytes_per_sample = bit_depth // 8
        self.rms_threshold = rms_threshold
        self.silence_timeout_sec = silence_timeout_sec
        self.max_duration_sec = max_duration_sec

        # Buffer to keep bytes
        self.buffer = bytearray()
        
        # State tracking for VAD (Voice Activity Detection)
        self.has_speech_started = False
        self.silence_accumulated_seconds = 0.0
        self.speech_ended = False

        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    def add_chunk(self, chunk: bytes) -> None:
        """
        Appends raw PCM audio bytes to the ingestion buffer and evaluates silence detection.
        """
        self.buffer.extend(chunk)

        # Convert chunk to numpy array (16-bit signed integers) for energy computation
        if len(chunk) >= self.bytes_per_sample:
            # We round length to match 2 bytes boundary
            aligned_len = (len(chunk) // self.bytes_per_sample) * self.bytes_per_sample
            samples = np.frombuffer(chunk[:aligned_len], dtype=np.int16)
            
            # Compute energy (RMS)
            if len(samples) > 0:
                rms = np.sqrt(np.mean(np.square(samples.astype(np.float64))))
            else:
                rms = 0.0
            
            # Calculate duration of the chunk in seconds
            chunk_duration = len(samples) / self.sample_rate
            
            # Evaluate energy
            if rms < self.rms_threshold:
                if self.has_speech_started:
                    self.silence_accumulated_seconds += chunk_duration
                    if self.silence_accumulated_seconds >= self.silence_timeout_sec:
                        self.speech_ended = True
                        logger.info(f"Silence detected: {self.silence_accumulated_seconds:.2f}s accumulated (Threshold: {self.rms_threshold}, RMS: {rms:.2f}). Ending speech.")
            else:
                # Speech activity detected
                if not self.has_speech_started:
                    self.has_speech_started = True
                    logger.info(f"Speech activity started (RMS: {rms:.2f}).")
                self.silence_accumulated_seconds = 0.0

            # Safety check: check max duration limit
            current_duration = len(self.buffer) / (self.sample_rate * self.bytes_per_sample)
            if current_duration >= self.max_duration_sec:
                self.speech_ended = True
                logger.info(f"Max duration limit reached ({current_duration:.2f}s / {self.max_duration_sec}s). Ending speech.")

    def has_speech_ended(self) -> bool:
        """
        Returns True if VAD silence/timeout indicates speech has ended.
        """
        return self.speech_ended

    def get_duration(self) -> float:
        """
        Returns the duration of the current audio buffer in seconds.
        """
        return len(self.buffer) / (self.sample_rate * self.bytes_per_sample)

    def save_buffer_to_wav(self, device_id: str) -> str:
        """
        Saves the current PCM buffer to a WAV file and returns the file path.
        Clears the buffer and resets VAD state.
        """
        if not self.buffer:
            logger.warning("Attempted to save empty audio buffer.")
            return ""

        # Naming convention: device_id + timestamp
        timestamp = int(time.time() * 1000)
        filename = f"{device_id}_{timestamp}.wav"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Convert buffer to numpy array (make a copy to release the memory view of self.buffer)
        samples = np.frombuffer(self.buffer, dtype=np.int16).copy()

        # Write WAV using soundfile
        sf.write(file_path, samples, self.sample_rate, subtype='PCM_16')
        logger.info(f"Saved audio segment: {file_path} (size: {len(self.buffer)} bytes, duration: {self.get_duration():.2f}s)")

        # Clear state
        self.clear()

        return file_path

    def clear(self) -> None:
        """
        Clears buffer and resets VAD state.
        """
        self.buffer.clear()
        self.has_speech_started = False
        self.silence_accumulated_seconds = 0.0
        self.speech_ended = False


def validate_and_convert_audio(file_path: str) -> str:
    """
    Reads an audio file, checks format (sample rate, channels, bit depth),
    and converts it to standard 16kHz, mono, 16-bit PCM WAV if invalid.
    Returns the path to the valid file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Read info
    info = sf.info(file_path)
    logger.info(f"Validating file {os.path.basename(file_path)}: rate={info.samplerate}Hz, channels={info.channels}, subtype={info.subtype}")

    # Flag to see if we need conversion
    needs_conversion = False

    if info.samplerate != 16000:
        needs_conversion = True
    if info.channels != 1:
        needs_conversion = True
    if info.subtype != 'PCM_16':
        needs_conversion = True

    if not needs_conversion:
        logger.info("Audio format is valid. No conversion needed.")
        return file_path

    logger.info("Audio format invalid. Converting to 16kHz, mono, 16-bit PCM WAV...")

    # Read raw audio
    data, samplerate = sf.read(file_path)

    # 1. Channel conversion (Stereo -> Mono)
    if len(data.shape) > 1 and data.shape[1] > 1:
        logger.info("Downmixing stereo audio to mono...")
        data = np.mean(data, axis=1)

    # 2. Resampling (original rate -> 16000Hz)
    if samplerate != 16000:
        logger.info(f"Resampling from {samplerate}Hz to 16000Hz...")
        # Linear interpolation resampling
        duration = len(data) / samplerate
        target_length = int(duration * 16000)
        data = np.interp(
            np.linspace(0, len(data), target_length, endpoint=False),
            np.arange(len(data)),
            data
        )

    # Save to a new validated file path
    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    name_parts = os.path.splitext(base_name)
    converted_filename = f"{name_parts[0]}_validated.wav"
    converted_path = os.path.join(dir_name, converted_filename)

    # Write converted file
    sf.write(converted_path, data, 16000, subtype='PCM_16')
    logger.info(f"Saved validated file: {converted_path}")

    # Remove the invalid original file to keep uploads directory clean (if it was an upload)
    try:
        os.remove(file_path)
        logger.info(f"Removed original invalid file: {file_path}")
    except Exception as e:
        logger.warning(f"Could not remove original file {file_path}: {e}")

    return converted_path
