# Learning 8 — Database Persistence: ORMs, Migrations, Async DB, Relational Schema

> **Capstone Step 8 Study Guide** — Interview-focused reference covering PostgreSQL, SQLAlchemy, Alembic, and async database patterns used in this project.

---

## 1. Why PostgreSQL Over SQLite / MongoDB?

| Criterion | SQLite | PostgreSQL | MongoDB |
|-----------|--------|------------|---------|
| Setup complexity | Zero (file-based) | Moderate (server process) | Moderate |
| Concurrent writes | ❌ Single writer | ✅ MVCC — many concurrent | ✅ |
| Relational schema | ✅ | ✅ | ❌ (document model) |
| Production-readiness | Small apps only | ✅ Industry standard | ✅ |
| JSON support | Limited | ✅ JSONB (indexed) | Native |
| Async driver | `aiosqlite` | **asyncpg** (fastest) | `motor` |

**Why PostgreSQL here?**  
Our data is naturally relational (devices → sessions → translations). We also need concurrent access from WebSocket frames and REST calls arriving simultaneously. PostgreSQL with asyncpg is the gold standard for async Python backends.

**When SQLite is better:** tiny single-user tools, embedded devices, test fixtures — anywhere that "zero-setup" outweighs concurrency needs.

---

## 2. SQLAlchemy ORM Concepts

### 2.1 Declarative Base

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    id = Column(String(36), primary_key=True)
```

- `Base` is the metaclass registry. Every model must inherit from it.  
- SQLAlchemy maps **class ↔ table**, **instance ↔ row**, **attribute ↔ column**.

### 2.2 Relationships

```python
# One device → many sessions
sessions = relationship("Session", back_populates="device", cascade="all, delete-orphan")
```

- `back_populates` creates a two-way link between model classes.  
- `cascade="all, delete-orphan"` means deleting a Device automatically deletes its child Sessions.  
- FK side: `device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"))`

> **Interview tip:** "back_populates vs backref" — `back_populates` is explicit and preferred; `backref` creates the reverse side implicitly but is less readable.

### 2.3 Column Types Used

| Column Type | Python equivalent | Notes |
|-------------|------------------|-------|
| `String(n)` | `str` | Fixed max length; uses `VARCHAR(n)` in SQL |
| `Text` | `str` | Unlimited length |
| `Float` | `float` | Maps to SQL `FLOAT` / `REAL` |
| `Integer` | `int` | 32-bit integer |
| `Boolean` | `bool` | `BOOLEAN` in PG |
| `DateTime(timezone=True)` | `datetime` | Always store UTC; PG `TIMESTAMPTZ` |
| `JSON` | `dict / list` | PG `JSON`; use `JSONB` for indexed queries |

---

## 3. Async SQLAlchemy with asyncpg

### 3.1 Why asyncpg?

Standard `psycopg2` blocks the event loop — catastrophic in async FastAPI. `asyncpg` is a pure-Python async PostgreSQL driver (no libpq). It's the fastest Python driver for Postgres.

### 3.2 Async Engine and Session

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# "postgresql+asyncpg://" tells SQLAlchemy to use asyncpg
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/mydb",
    echo=False,
    pool_pre_ping=True,   # sends a SELECT 1 before each connection checkout
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # prevents lazy-load errors after commit
    autocommit=False,
    autoflush=False,
)
```

> **`expire_on_commit=False`:** By default SQLAlchemy expires all attributes after a commit, forcing a DB round-trip on next access. In async code that round-trip may happen outside the session context → `MissingGreenlet` error. Setting this to `False` keeps the last-committed values in memory.

### 3.3 Dependency Injection in FastAPI

```python
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# In endpoint:
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...
```

FastAPI calls `get_db()` before the endpoint, yields the session in, and cleans it up after the response is sent — even on exceptions.

### 3.4 Writing Queries

```python
# SELECT with filter
result = await db.execute(select(Device).where(Device.device_id == "ESP32_001"))
device = result.scalar_one_or_none()

# INSERT
db.add(new_device)
await db.commit()
await db.refresh(new_device)   # reloads server-generated defaults (e.g. timestamps)

# UPDATE
await db.execute(
    update(DBSession)
    .where(DBSession.id == session_id)
    .values(is_active=False)
)
await db.commit()
```

> **`scalar_one_or_none()`** returns one row or `None`. `scalar_one()` raises if no row found. `scalars().all()` returns a list.

---

## 4. Alembic Migrations

### 4.1 What Is a Migration?

A migration is a versioned Python script that applies incremental schema changes to the database. Instead of dropping and recreating tables, migrations let you evolve the schema safely in production.

```
alembic upgrade head    # apply all unapplied migrations
alembic downgrade -1    # roll back the last migration
alembic history         # show the revision chain
alembic current         # show which revision the DB is at
```

### 4.2 Revision Chain

```
None ← 001_initial_schema ← 002_add_user_email ← ...
```

Each migration stores `revision` (its own ID) and `down_revision` (the previous ID). Alembic walks this chain to decide what to apply.

### 4.3 Autogenerate

```bash
alembic revision --autogenerate -m "add_email_column"
```

Alembic compares `Base.metadata` (your ORM model definitions) against the live DB schema, then generates an `upgrade()` diff. **Always review generated migrations** — autogenerate misses some things (e.g. partial indexes, custom constraints).

### 4.4 Async env.py Pattern

Default Alembic env.py is synchronous. For async SQLAlchemy you need:

```python
from sqlalchemy.ext.asyncio import async_engine_from_config

async def run_async_migrations():
    connectable = async_engine_from_config(...)
    async with connectable.connect() as conn:
        await conn.run_sync(do_run_migrations)

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

`run_sync()` runs synchronous Alembic context code inside the async connection — the standard bridge pattern.

---

## 5. Relational Schema Design

### 5.1 Our Schema

```
devices (id PK, device_id UNIQUE, name, registered_at, last_seen_at, is_active, metadata JSON)
    │
    ├── users (id PK, device_id FK, username UNIQUE, preferred_source/target_lang)
    │
    └── sessions (id PK, device_id FK, started_at, ended_at, source_lang, target_lang, is_active, total_utterances)
            │
            └── translations (id PK, session_id FK, device_id FK, audio_filename,
                              original_text, translated_text, tts_filename,
                              asr/lid/translation/tts/total_latency_sec, status, error_message, created_at)
```

### 5.2 Design Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| UUID PKs (String) | No integer sequence contention; safe for distributed inserts; portable across DBs |
| `device_id` denormalized in `translations` | Avoids JOIN through sessions table for per-device history queries |
| `total_utterances` counter in `sessions` | Cheaper than `COUNT(*)` on translations at query time; updated atomically |
| `metadata` as JSON | Device firmware version, MAC address, etc. are schema-free; avoids extra table |
| `DateTime(timezone=True)` everywhere | Always UTC; timezone-aware prevents subtle bugs when server timezone changes |

### 5.3 Normalization Levels

- **1NF**: All columns atomic (no repeating groups).
- **2NF**: All non-key columns depend on the full PK (no partial dependency — our PKs are single-column UUIDs).
- **3NF**: No transitive dependencies (e.g. device name doesn't depend on session — it's in the devices table).

---

## 6. Pagination Pattern

```python
# Count + paginated data — two queries
count_stmt = select(func.count()).select_from(main_stmt.subquery())
total = (await db.execute(count_stmt)).scalar_one()

paginated = main_stmt.order_by(Translation.created_at.desc()).limit(limit).offset(offset)
rows = (await db.execute(paginated)).scalars().all()
```

> **Interview tip:** Why not use `.count()` on the ORM object? `func.count()` with a subquery is more explicit and works correctly with complex filters.

---

## 7. Integration with the FastAPI Pipeline

### Flow with DB logging

```
POST /audio/transcribe
  → PipelineOrchestrator.run(db=db)
      → ASR → LID → Translation → TTS
      → db_service.register_device(db, device_id)
      → db_service.log_translation(db, device_id, result)
  ← JSON response (unchanged from Step 7)

GET /api/v1/history?device_id=ESP32_001&limit=20
  → db_service.get_history(db, device_id="ESP32_001")
  ← { total, offset, limit, items: [...] }

GET /api/v1/devices
  → db_service.get_devices(db)
  ← { total, items: [...] }
```

### Non-blocking design

The DB `log_translation` call is wrapped in a `try/except` inside the orchestrator. If the DB is unavailable, the pipeline **still returns the translation result** — persistence failures never break the real-time audio path.

---

## 8. Common Interview Questions

**Q: What is N+1 query problem and how do you avoid it?**  
A: Accessing a relationship (e.g. `device.sessions`) in a loop triggers one query per loop iteration. Fix with eager loading: `select(Device).options(selectinload(Device.sessions))`.

**Q: What's the difference between `Session.commit()` and `Session.flush()`?**  
A: `flush()` writes pending changes to the DB (within the current transaction) but doesn't commit. Useful to get a DB-generated ID before committing. `commit()` finalises the transaction.

**Q: Why use `expire_on_commit=False`?**  
A: After `commit()`, SQLAlchemy expires all instance attributes. In async code, re-accessing them triggers a new query — but if the session is already closed, it raises `DetachedInstanceError`. Disabling expiry keeps the last committed values in memory, safe to use after the session closes.

**Q: What does `pool_pre_ping=True` do?**  
A: Before handing a connection from the pool to a caller, SQLAlchemy sends a cheap `SELECT 1`. If the DB has closed the connection (e.g. after a restart), the stale connection is recycled and a fresh one is created — prevents `connection closed` errors in long-running servers.

**Q: Alembic `upgrade` vs `stamp`?**  
A: `upgrade head` runs all pending migrations. `stamp head` just marks the DB as being at the latest revision without running SQL — useful when you've already created tables manually (e.g. via `create_all`) and want Alembic to take over from that point.

---

## 9. Commands Quick Reference

```bash
# Apply all migrations
poetry run alembic upgrade head

# Roll back last migration
poetry run alembic downgrade -1

# Generate a new migration from model changes
poetry run alembic revision --autogenerate -m "add_user_email"

# Check which migration the DB is on
poetry run alembic current

# Show full revision history
poetry run alembic history --verbose

# Stamp DB as being at latest revision (skips running migrations)
poetry run alembic stamp head
```

---

*Step 8 complete. Next: Step 9 — Authentication & Authorization (JWT tokens, device API keys).*
