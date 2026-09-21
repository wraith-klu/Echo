"""
conftest.py — Shared pytest fixtures for the Speech Translation Backend test suite.

Fixtures defined here are available to ALL test files in this package automatically.
"""

import io
import os
import struct
import tempfile
import numpy as np
import pytest
import pytest_asyncio

from unittest.mock import MagicMock, AsyncMock

# ---------------------------------------------------------------------------
# Ensure the backend root is on sys.path when running pytest from the repo root
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    amplitude: int = 2000,
    silence: bool = False,
) -> bytes:
    """
    Generate a minimal valid WAV file in memory.
    If silence=True the signal is zeroed (simulates no speech).
    Returns raw bytes suitable for writing to a .wav file.
    """
    n_samples = int(sample_rate * duration_sec)
    if silence:
        samples = np.zeros(n_samples, dtype=np.int16)
    else:
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        samples = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.int16)

    buf = io.BytesIO()
    # Write RIFF header
    data_bytes = samples.tobytes()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(data_bytes)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(data_bytes)))
    buf.write(data_bytes)
    return buf.getvalue()


@pytest.fixture
def sample_wav_path(tmp_path) -> str:
    """Write a 2-second 440 Hz sine wave WAV to a temp file and return its path."""
    path = tmp_path / "sample.wav"
    path.write_bytes(_make_wav_bytes(duration_sec=2.0))
    return str(path)


@pytest.fixture
def silence_wav_path(tmp_path) -> str:
    """Write a 2-second silent WAV to a temp file and return its path."""
    path = tmp_path / "silence.wav"
    path.write_bytes(_make_wav_bytes(duration_sec=2.0, silence=True))
    return str(path)


@pytest.fixture
def pcm_chunk() -> bytes:
    """Return a small chunk of raw 16-bit PCM audio bytes (non-silent)."""
    n = 1600  # 100 ms at 16 kHz
    t = np.linspace(0, 0.1, n, endpoint=False)
    samples = (2000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    return samples.tobytes()


@pytest.fixture
def silent_pcm_chunk() -> bytes:
    """Return raw 16-bit PCM bytes that are pure silence."""
    return np.zeros(1600, dtype=np.int16).tobytes()


# ---------------------------------------------------------------------------
# Mock ML model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_asr_service():
    """A mock TranscriptionService that returns a canned ASR result."""
    svc = MagicMock()
    svc.transcribe_audio.return_value = {
        "text": "Hello, how are you?",
        "language": "en",
        "language_probability": 0.99,
        "segments": [{"start": 0.0, "end": 1.5, "text": "Hello, how are you?"}],
        "latency_sec": 0.5,
    }
    return svc


@pytest.fixture
def mock_translation_service():
    """A mock TranslationService that returns a canned translation result."""
    svc = MagicMock()
    svc.translate_text.return_value = {
        "translated_text": "Hola, ¿cómo estás?",
        "source_lang": "en",
        "target_lang": "es",
        "source_nllb": "eng_Latn",
        "target_nllb": "spa_Latn",
        "latency_sec": 0.8,
    }
    return svc


@pytest.fixture
def mock_tts_service():
    """A mock TTSService that returns a minimal valid WAV bytes payload."""
    svc = MagicMock()
    svc.synthesize_speech.return_value = _make_wav_bytes(duration_sec=1.0)
    return svc


@pytest.fixture
def mock_ml_models(mock_asr_service, mock_translation_service, mock_tts_service):
    """Combined ml_models dict as used by the pipeline orchestrator."""
    return {
        "asr": mock_asr_service,
        "translation": mock_translation_service,
        "tts": mock_tts_service,
    }


# ---------------------------------------------------------------------------
# Async DB session fixture (in-memory SQLite for unit tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session():
    """
    Provides an async SQLAlchemy session backed by an in-memory SQLite database.
    Creates all tables before the test and drops them after.

    NOTE: asyncpg requires PostgreSQL; for unit tests we swap in aiosqlite.
    Install: poetry add aiosqlite --dev
    """
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.core.database import Base
        import app.models.db  # noqa: F401 — register models

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with SessionLocal() as session:
            yield session

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    except ImportError:
        pytest.skip("aiosqlite not installed — skipping DB fixture")
