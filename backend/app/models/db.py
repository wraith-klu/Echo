"""
SQLAlchemy ORM models for the Speech Translation Backend.

Tables:
  - devices     : Registered ESP32 (or other) client devices
  - users       : Optional user profiles linked to devices
  - sessions    : A single conversation/streaming session per device
  - translations: Individual translated utterances inside a session
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Helper: generate a UUID4 string as default primary key
# ---------------------------------------------------------------------------
def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
class Device(Base):
    """
    Represents a physical device (e.g. ESP32) that connects to the backend.

    Columns:
        id          : UUID primary key (string form for portability)
        device_id   : Human-readable unique identifier set by the device firmware
        name        : Friendly display name (e.g. "Desk ESP32")
        description : Optional free-form notes
        registered_at: First seen / registration timestamp
        last_seen_at : Updated each time the device connects
        is_active   : Soft-delete / enable flag
        metadata    : Arbitrary JSON payload for firmware version, MAC address, etc.
    """
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    device_id = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    registered_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    meta = Column("metadata", JSON, nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="device", cascade="all, delete-orphan")
    users = relationship("User", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device id={self.id!r} device_id={self.device_id!r}>"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    """
    Optional user profile that can be linked to a device.

    Columns:
        id         : UUID primary key
        device_id  : FK → devices.id (one device, one primary user for now)
        username   : Unique display name
        preferred_source_language : BCP-47 tag (e.g. 'en', 'fr')
        preferred_target_language : BCP-47 tag (e.g. 'es', 'hi')
        created_at : Account creation timestamp
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    preferred_source_language = Column(String(16), nullable=True, default="en")
    preferred_target_language = Column(String(16), nullable=True, default="es")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="users")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r}>"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class Session(Base):
    """
    A single streaming/conversation session opened by a device.

    A session groups multiple Translation records so you can replay an
    entire conversation or compute aggregate statistics (total latency, etc.).

    Columns:
        id           : UUID primary key
        device_id    : FK → devices.id
        started_at   : Session open timestamp
        ended_at     : Session close timestamp (NULL = still active)
        source_lang  : Dominant source language for this session
        target_lang  : Requested target language for this session
        is_active    : True while the WebSocket connection is open
        total_utterances : Denormalised count, updated on each translation log
    """
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    source_lang = Column(String(16), nullable=True)
    target_lang = Column(String(16), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    total_utterances = Column(Integer, default=0, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="sessions")
    translations = relationship("Translation", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Session id={self.id!r} device_id={self.device_id!r} active={self.is_active}>"


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
class Translation(Base):
    """
    A single transcribed + translated utterance produced by the pipeline.

    Columns:
        id                   : UUID primary key
        session_id           : FK → sessions.id
        device_id            : Denormalised FK → devices.id (fast per-device queries)
        audio_filename       : Name of the source audio file saved on disk
        audio_duration_sec   : Duration of the source WAV
        source_lang          : Detected / override source language code
        target_lang          : Requested target language code
        original_text        : Raw ASR transcription
        translated_text      : Output of the translation model
        tts_filename         : Name of the generated TTS WAV file (nullable)
        asr_latency_sec      : Time taken by the ASR stage
        lid_latency_sec      : Time taken by language detection
        translation_latency_sec: Time taken by the translation stage
        tts_latency_sec      : Time taken by TTS synthesis
        total_latency_sec    : End-to-end pipeline wall time
        status               : "success" | "partial_success" | "error"
        error_message        : Non-null if a stage failed
        created_at           : Row insertion timestamp
    """
    __tablename__ = "translations"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)

    # Audio source
    audio_filename = Column(String(512), nullable=True)
    audio_duration_sec = Column(Float, nullable=True)

    # Languages
    source_lang = Column(String(16), nullable=True)
    target_lang = Column(String(16), nullable=True)

    # Text content
    original_text = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)

    # TTS output
    tts_filename = Column(String(512), nullable=True)

    # Latency breakdown (seconds)
    asr_latency_sec = Column(Float, nullable=True)
    lid_latency_sec = Column(Float, nullable=True)
    translation_latency_sec = Column(Float, nullable=True)
    tts_latency_sec = Column(Float, nullable=True)
    total_latency_sec = Column(Float, nullable=True)

    # Result
    status = Column(String(32), default="success", nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="translations")

    def __repr__(self) -> str:
        return (
            f"<Translation id={self.id!r} src={self.source_lang!r} "
            f"tgt={self.target_lang!r} status={self.status!r}>"
        )
