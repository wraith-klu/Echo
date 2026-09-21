"""
test_ingestion.py — Unit tests for the AudioIngestionService (Step 2).

Tests cover:
  - PCM chunk buffering
  - RMS-based voice activity detection (VAD)
  - Silence timeout triggering speech_ended
  - Max duration cap
  - WAV file validation and conversion
"""

import os
import struct
import numpy as np
import pytest

from app.services.ingestion import AudioIngestionService, validate_and_convert_audio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sine_chunk(freq=440, duration_ms=100, sample_rate=16000, amplitude=3000) -> bytes:
    n = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n, endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16).tobytes()


def _silent_chunk(duration_ms=100, sample_rate=16000) -> bytes:
    n = int(sample_rate * duration_ms / 1000)
    return np.zeros(n, dtype=np.int16).tobytes()


# ---------------------------------------------------------------------------
# AudioIngestionService unit tests
# ---------------------------------------------------------------------------

class TestAudioIngestionService:

    def test_initial_state(self):
        svc = AudioIngestionService()
        assert svc.has_speech_started is False
        assert svc.speech_ended is False
        assert len(svc.buffer) == 0

    def test_silence_does_not_start_speech(self):
        svc = AudioIngestionService(rms_threshold=500.0)
        for _ in range(10):
            svc.add_chunk(_silent_chunk())
        assert svc.has_speech_started is False

    def test_loud_chunk_starts_speech(self):
        svc = AudioIngestionService(rms_threshold=500.0)
        svc.add_chunk(_sine_chunk(amplitude=3000))
        assert svc.has_speech_started is True

    def test_silence_after_speech_triggers_ended(self):
        svc = AudioIngestionService(rms_threshold=500.0, silence_timeout_sec=0.3)
        # Trigger speech
        svc.add_chunk(_sine_chunk(amplitude=3000, duration_ms=200))
        assert svc.has_speech_started is True

        # Feed enough silence chunks to exceed timeout (0.3 s = 300 ms)
        for _ in range(4):  # 4 × 100 ms = 400 ms of silence
            svc.add_chunk(_silent_chunk(duration_ms=100))

        assert svc.speech_ended is True

    def test_max_duration_triggers_ended(self):
        svc = AudioIngestionService(rms_threshold=500.0, max_duration_sec=0.3)
        # Feed 400 ms of loud audio
        for _ in range(4):
            svc.add_chunk(_sine_chunk(amplitude=3000, duration_ms=100))
        assert svc.speech_ended is True

    def test_buffer_accumulates(self):
        svc = AudioIngestionService()
        chunk = _sine_chunk(duration_ms=100)
        svc.add_chunk(chunk)
        svc.add_chunk(chunk)
        assert len(svc.buffer) == len(chunk) * 2

    def test_reset_clears_state(self):
        svc = AudioIngestionService(rms_threshold=500.0)
        svc.add_chunk(_sine_chunk(amplitude=3000))
        assert svc.has_speech_started is True
        svc.clear()
        assert svc.has_speech_started is False
        assert svc.speech_ended is False
        assert len(svc.buffer) == 0


# ---------------------------------------------------------------------------
# validate_and_convert_audio tests
# ---------------------------------------------------------------------------

class TestValidateAndConvertAudio:

    def test_valid_wav_passes(self, sample_wav_path):
        result = validate_and_convert_audio(sample_wav_path)
        assert os.path.exists(result)

    def test_result_is_16khz_mono(self, sample_wav_path):
        import soundfile as sf
        result = validate_and_convert_audio(sample_wav_path)
        info = sf.info(result)
        assert info.samplerate == 16000
        assert info.channels == 1

    def test_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            validate_and_convert_audio("/nonexistent/path/audio.wav")
