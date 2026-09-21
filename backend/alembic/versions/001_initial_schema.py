"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-25

Creates the four core tables:
    devices, users, sessions, translations
"""

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Alembic identifiers
# ---------------------------------------------------------------------------
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # devices
    # ------------------------------------------------------------------
    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("device_id", sa.String(128), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metadata", sa.JSON, nullable=True),
    )
    op.create_index("ix_devices_device_id", "devices", ["device_id"])

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            sa.String(36),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("username", sa.String(128), unique=True, nullable=False),
        sa.Column("preferred_source_language", sa.String(16), nullable=True, server_default="en"),
        sa.Column("preferred_target_language", sa.String(16), nullable=True, server_default="es"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_device_id", "users", ["device_id"])

    # ------------------------------------------------------------------
    # sessions
    # ------------------------------------------------------------------
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            sa.String(36),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_lang", sa.String(16), nullable=True),
        sa.Column("target_lang", sa.String(16), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("total_utterances", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_sessions_device_id", "sessions", ["device_id"])

    # ------------------------------------------------------------------
    # translations
    # ------------------------------------------------------------------
    op.create_table(
        "translations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "device_id",
            sa.String(36),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("audio_filename", sa.String(512), nullable=True),
        sa.Column("audio_duration_sec", sa.Float, nullable=True),
        sa.Column("source_lang", sa.String(16), nullable=True),
        sa.Column("target_lang", sa.String(16), nullable=True),
        sa.Column("original_text", sa.Text, nullable=True),
        sa.Column("translated_text", sa.Text, nullable=True),
        sa.Column("tts_filename", sa.String(512), nullable=True),
        sa.Column("asr_latency_sec", sa.Float, nullable=True),
        sa.Column("lid_latency_sec", sa.Float, nullable=True),
        sa.Column("translation_latency_sec", sa.Float, nullable=True),
        sa.Column("tts_latency_sec", sa.Float, nullable=True),
        sa.Column("total_latency_sec", sa.Float, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_translations_session_id", "translations", ["session_id"])
    op.create_index("ix_translations_device_id", "translations", ["device_id"])
    op.create_index("ix_translations_created_at", "translations", ["created_at"])


def downgrade() -> None:
    op.drop_table("translations")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("devices")
