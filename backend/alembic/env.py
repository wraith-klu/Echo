"""
Alembic environment configuration for async SQLAlchemy (asyncpg driver).

Key differences from the default env.py:
  - Uses AsyncEngine.connect() instead of synchronous engine_from_config
  - Pulls the DB URL from app.config.settings so there is a single source of truth
  - Imports all ORM models so autogenerate can diff against the live DB schema
"""

import asyncio
import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Ensure the backend package root (containing 'app/') is on sys.path
# ---------------------------------------------------------------------------
# When Alembic is run from `backend/`, this resolves to `backend/` itself.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ---------------------------------------------------------------------------
# Alembic Config object (wraps alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import models and set target_metadata for autogenerate
# ---------------------------------------------------------------------------
# All four models (Device, User, Session, Translation) must be imported so
# SQLAlchemy registers them with Base.metadata before autogenerate runs.
from app.core.database import Base           # noqa: E402
import app.models.db                         # noqa: E402, F401

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Inject the async database URL from app settings
# ---------------------------------------------------------------------------
from app.config import settings              # noqa: E402

# Override the sqlalchemy.url key with our runtime value
config.set_main_option("sqlalchemy.url", settings.async_database_url)


# ---------------------------------------------------------------------------
# Offline migrations (no live DB connection required)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL scripts to stdout or a file.
    No live DB connection is required.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (connects to a live DB using async engine)
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg driver)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode — wraps the async function in asyncio.run()."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Alembic entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
