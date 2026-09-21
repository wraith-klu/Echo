from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

_db_url = settings.async_database_url
_is_sqlite = _db_url.startswith("sqlite")

# SQLite needs check_same_thread=False for async use; PostgreSQL does not need connect_args
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# pool_pre_ping is not supported by aiosqlite; safe to enable only for PostgreSQL
engine = create_async_engine(
    _db_url,
    echo=False,
    future=True,
    pool_pre_ping=not _is_sqlite,
    connect_args=_connect_args,
)

# Async session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

async def get_db():
    """
    Dependency generator that provides an async SQLAlchemy session.
    Ensures the session is cleanly closed after the request is finished.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
