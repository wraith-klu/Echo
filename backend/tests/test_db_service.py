"""
test_db_service.py — Unit tests for database service layer (Step 8).

Uses the in-memory SQLite async session fixture from conftest.py.
Tests cover: register_device (upsert), create_session, log_translation,
get_history (pagination + filtering), get_devices.
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock

from app.services.db_service import (
    register_device,
    create_session,
    close_session,
    log_translation,
    get_history,
    get_devices,
    get_or_create_session,
)
from app.services.pipeline import PipelineResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline_result(status="success", has_translation=True, has_tts=True):
    """Build a minimal PipelineResult for DB logging tests."""
    translation = {
        "translated_text": "Hola, ¿cómo estás?",
        "target_lang": "es",
        "source_nllb": "eng_Latn",
        "target_nllb": "spa_Latn",
        "latency_sec": 0.8,
    } if has_translation else None

    tts = {
        "filename": "tts_test_123_es.wav",
        "file_path": "/tmp/tts_test_123_es.wav",
        "sample_rate": 16000,
        "channels": 1,
        "bit_depth": 16,
        "audio_size_bytes": 32000,
    } if has_tts else None

    return PipelineResult(
        status=status,
        filename="test_audio.wav",
        duration=2.5,
        message="Test pipeline result",
        transcription={
            "text": "Hello, how are you?",
            "segments": [],
            "language_detection": {"detected_language": "en", "confidence": 0.99, "source": "whisper"},
            "supported": True,
        },
        translation=translation,
        tts=tts,
        latencies={
            "asr_sec": 0.5,
            "lid_sec": 0.01,
            "translation_sec": 0.8,
            "tts_sec": 0.3,
            "total_sec": 1.61,
        },
        error=None if status != "error" else "Something failed",
    )


# ---------------------------------------------------------------------------
# Device tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_device_creates_new(db_session):
    device = await register_device(db_session, device_id="ESP32_001", name="Test Device")
    assert device.device_id == "ESP32_001"
    assert device.name == "Test Device"
    assert device.is_active is True


@pytest.mark.asyncio
async def test_register_device_upserts_existing(db_session):
    d1 = await register_device(db_session, device_id="ESP32_002")
    original_id = d1.id

    # Register again — should update, not create a duplicate
    d2 = await register_device(db_session, device_id="ESP32_002", name="Updated Name")
    assert d2.id == original_id
    assert d2.name == "Updated Name"


@pytest.mark.asyncio
async def test_get_devices_returns_all(db_session):
    await register_device(db_session, device_id="DEV_A")
    await register_device(db_session, device_id="DEV_B")
    devices = await get_devices(db_session)
    device_ids = [d.device_id for d in devices]
    assert "DEV_A" in device_ids
    assert "DEV_B" in device_ids


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_auto_registers_device(db_session):
    session = await create_session(db_session, device_id="NEW_DEVICE_XYZ")
    assert session.id is not None
    assert session.is_active is True
    assert session.total_utterances == 0


@pytest.mark.asyncio
async def test_close_session_marks_inactive(db_session):
    session = await create_session(db_session, device_id="CLOSE_TEST")
    await close_session(db_session, session_id=session.id)

    from sqlalchemy import select
    from app.models.db import Session as DBSession
    result = await db_session.execute(select(DBSession).where(DBSession.id == session.id))
    s = result.scalar_one()
    assert s.is_active is False
    assert s.ended_at is not None


@pytest.mark.asyncio
async def test_get_or_create_session_reuses_active(db_session):
    s1 = await get_or_create_session(db_session, device_id="REUSE_TEST")
    s2 = await get_or_create_session(db_session, device_id="REUSE_TEST")
    assert s1.id == s2.id  # same session reused


# ---------------------------------------------------------------------------
# Translation logging tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_translation_creates_row(db_session):
    await register_device(db_session, device_id="LOG_DEVICE")
    result = _make_pipeline_result()
    translation = await log_translation(db_session, device_id="LOG_DEVICE", pipeline_result=result)
    assert translation.id is not None
    assert translation.original_text == "Hello, how are you?"
    assert translation.translated_text == "Hola, ¿cómo estás?"
    assert translation.status == "success"


@pytest.mark.asyncio
async def test_log_translation_increments_session_counter(db_session):
    session = await create_session(db_session, device_id="COUNTER_DEVICE")
    result = _make_pipeline_result()

    await log_translation(db_session, device_id="COUNTER_DEVICE",
                          pipeline_result=result, session_id=session.id)
    await log_translation(db_session, device_id="COUNTER_DEVICE",
                          pipeline_result=result, session_id=session.id)

    from sqlalchemy import select
    from app.models.db import Session as DBSession
    r = await db_session.execute(select(DBSession).where(DBSession.id == session.id))
    s = r.scalar_one()
    assert s.total_utterances == 2


# ---------------------------------------------------------------------------
# History / pagination tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_returns_all(db_session):
    await register_device(db_session, device_id="HIST_DEVICE")
    r = _make_pipeline_result()
    for _ in range(3):
        await log_translation(db_session, device_id="HIST_DEVICE", pipeline_result=r)

    hist = await get_history(db_session, device_id="HIST_DEVICE")
    assert hist["total"] == 3
    assert len(hist["items"]) == 3


@pytest.mark.asyncio
async def test_get_history_pagination(db_session):
    await register_device(db_session, device_id="PAGE_DEVICE")
    r = _make_pipeline_result()
    for _ in range(5):
        await log_translation(db_session, device_id="PAGE_DEVICE", pipeline_result=r)

    hist = await get_history(db_session, device_id="PAGE_DEVICE", limit=2, offset=0)
    assert len(hist["items"]) == 2
    assert hist["total"] == 5


@pytest.mark.asyncio
async def test_get_history_unknown_device_returns_empty(db_session):
    hist = await get_history(db_session, device_id="NONEXISTENT_DEVICE")
    assert hist["total"] == 0
    assert hist["items"] == []
