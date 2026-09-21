"""
db_service.py — Async database service helpers for the translation backend.

All functions accept an AsyncSession (injected via FastAPI's get_db dependency
or passed directly from the pipeline orchestrator).

Functions:
    register_device       : Upsert a Device row (create or touch last_seen_at)
    create_session        : Open a new Session row for a device
    close_session         : Mark a session as ended
    log_translation       : Insert a Translation row and increment session counter
    get_history           : Paginated list of Translation rows (optionally filtered)
    get_devices           : List all registered Device rows
    get_or_create_session : Convenience — find active session or create a new one
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.db import Device, Session as DBSession, Translation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Device helpers
# ---------------------------------------------------------------------------

async def register_device(
    db: AsyncSession,
    device_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Device:
    """
    Upsert a device by its device_id.
    - If the device does not exist → create and return it.
    - If it already exists → update last_seen_at (and name/meta if provided) and return it.
    """
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if device is None:
        device = Device(
            id=str(uuid.uuid4()),
            device_id=device_id,
            name=name or device_id,
            description=description,
            registered_at=_utcnow(),
            last_seen_at=_utcnow(),
            is_active=True,
            meta=meta,
        )
        db.add(device)
        logger.info(f"[DB] Registered new device: {device_id!r}")
    else:
        device.last_seen_at = _utcnow()
        if name:
            device.name = name
        if meta:
            device.meta = meta
        logger.debug(f"[DB] Updated last_seen_at for device: {device_id!r}")

    await db.commit()
    await db.refresh(device)
    return device


async def get_devices(
    db: AsyncSession,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[Device]:
    """Return a paginated list of all registered devices."""
    stmt = select(Device)
    if active_only:
        stmt = stmt.where(Device.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Device.registered_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

async def create_session(
    db: AsyncSession,
    device_id: str,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
) -> DBSession:
    """
    Open a new session for the given device_id (by internal UUID).
    First resolves the device row; if not found, auto-registers the device.
    """
    # Resolve device
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        device = await register_device(db, device_id=device_id)

    session = DBSession(
        id=str(uuid.uuid4()),
        device_id=device.id,
        started_at=_utcnow(),
        source_lang=source_lang,
        target_lang=target_lang,
        is_active=True,
        total_utterances=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info(f"[DB] Created session {session.id!r} for device {device_id!r}")
    return session


async def close_session(db: AsyncSession, session_id: str) -> None:
    """Mark a session as inactive and record its end time."""
    await db.execute(
        update(DBSession)
        .where(DBSession.id == session_id)
        .values(is_active=False, ended_at=_utcnow())
    )
    await db.commit()
    logger.info(f"[DB] Closed session {session_id!r}")


async def get_or_create_session(
    db: AsyncSession,
    device_id: str,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
) -> DBSession:
    """
    Find the most recent active session for this device_id.
    If none exists, create and return a new one.
    """
    # Resolve device → get internal UUID
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        device = await register_device(db, device_id=device_id)

    stmt = (
        select(DBSession)
        .where(DBSession.device_id == device.id, DBSession.is_active == True)  # noqa: E712
        .order_by(DBSession.started_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session is None:
        session = await create_session(db, device_id=device_id, source_lang=source_lang, target_lang=target_lang)

    return session


# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

async def log_translation(
    db: AsyncSession,
    device_id: str,
    pipeline_result,  # PipelineResult dataclass — imported lazily to avoid circular imports
    session_id: Optional[str] = None,
) -> Translation:
    """
    Persist a completed pipeline result as a Translation row.

    Args:
        db             : Active async DB session
        device_id      : Device identifier string (firmware ID)
        pipeline_result: PipelineResult dataclass from pipeline.py
        session_id     : Optional explicit session UUID; if None, auto-resolves

    Returns:
        The newly created Translation ORM object.
    """
    # Resolve device internal UUID
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    device_uuid = device.id if device else None

    # Extract fields from PipelineResult
    tr = pipeline_result.transcription or {}
    tl = pipeline_result.translation or {}
    tts = pipeline_result.tts or {}
    lat = pipeline_result.latencies or {}

    lid_info = tr.get("language_detection", {})
    source_lang = lid_info.get("detected_language") or None
    target_lang = tl.get("target_lang") or None

    translation = Translation(
        id=str(uuid.uuid4()),
        session_id=session_id,
        device_id=device_uuid,
        audio_filename=pipeline_result.filename,
        audio_duration_sec=pipeline_result.duration,
        source_lang=source_lang,
        target_lang=target_lang,
        original_text=tr.get("text"),
        translated_text=tl.get("translated_text"),
        tts_filename=tts.get("filename"),
        asr_latency_sec=lat.get("asr_sec"),
        lid_latency_sec=lat.get("lid_sec"),
        translation_latency_sec=lat.get("translation_sec"),
        tts_latency_sec=lat.get("tts_sec"),
        total_latency_sec=lat.get("total_sec"),
        status=pipeline_result.status,
        error_message=pipeline_result.error,
        created_at=_utcnow(),
    )
    db.add(translation)

    # Increment session counter if a session_id was provided
    if session_id:
        await db.execute(
            update(DBSession)
            .where(DBSession.id == session_id)
            .values(total_utterances=DBSession.total_utterances + 1)
        )

    await db.commit()
    await db.refresh(translation)
    logger.info(
        f"[DB] Logged translation {translation.id!r} | "
        f"device={device_id!r} status={translation.status!r}"
    )
    return translation


# ---------------------------------------------------------------------------
# History query helpers
# ---------------------------------------------------------------------------

async def get_history(
    db: AsyncSession,
    device_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Return paginated translation history with a total row count.

    Filters:
        device_id  : Filter by device firmware string (resolved to internal UUID)
        session_id : Filter by session UUID
    """
    stmt = select(Translation)

    if device_id:
        res = await db.execute(select(Device.id).where(Device.device_id == device_id))
        device_uuid = res.scalar_one_or_none()
        if device_uuid:
            stmt = stmt.where(Translation.device_id == device_uuid)
        else:
            # Device not found → return empty result immediately
            return {"total": 0, "offset": offset, "limit": limit, "items": []}

    if session_id:
        stmt = stmt.where(Translation.session_id == session_id)

    # Total count (without pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated data
    stmt = stmt.order_by(Translation.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_translation_to_dict(r) for r in rows],
    }


def _translation_to_dict(t: Translation) -> Dict[str, Any]:
    return {
        "id": t.id,
        "session_id": t.session_id,
        "device_id": t.device_id,
        "audio_filename": t.audio_filename,
        "audio_duration_sec": t.audio_duration_sec,
        "source_lang": t.source_lang,
        "target_lang": t.target_lang,
        "original_text": t.original_text,
        "translated_text": t.translated_text,
        "tts_filename": t.tts_filename,
        "latencies": {
            "asr_sec": t.asr_latency_sec,
            "lid_sec": t.lid_latency_sec,
            "translation_sec": t.translation_latency_sec,
            "tts_sec": t.tts_latency_sec,
            "total_sec": t.total_latency_sec,
        },
        "status": t.status,
        "error_message": t.error_message,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
