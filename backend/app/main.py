import warnings

# ── Suppress noisy third-party warnings that are non-actionable in this project ──
# pydub: ffmpeg not on PATH (we use soundfile for conversion instead)
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg", category=RuntimeWarning)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logger import logger
from app.core.database import Base, engine
from app.api.v1.router import api_router
from app.services.transcription import TranscriptionService
from app.services.translation import TranslationService

# Import models so SQLAlchemy registers them with Base.metadata
import app.models.db  # noqa: F401

# Dictionary to hold resources loaded during startup (e.g. AI models)
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────
    logger.info("Initializing Echo speech translation backend...")
    logger.info(f"Project name: {settings.PROJECT_NAME}")

    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified / created.")
    except Exception as e:
        logger.warning(
            f"DB unavailable at startup — tables not created. "
            f"Start PostgreSQL or set DATABASE_URL to enable persistence. Error: {type(e).__name__}"
        )

    # ── Load Whisper ASR model (tiny for free-tier RAM) ────────
    try:
        logger.info(f"Loading Whisper '{settings.WHISPER_MODEL_NAME}' ASR model...")
        ml_models["asr"] = TranscriptionService(
            model_name=settings.WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
        )
        logger.info("Whisper ASR model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load ASR Whisper model: {e}", exc_info=True)

    # ── Initialize Translation service (Gemini API — no weights to load) ──
    try:
        logger.info("Initializing Translation service (Gemini Flash API)...")
        ml_models["translation"] = TranslationService()
        logger.info("Translation service initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Translation service: {e}", exc_info=True)

    # ── TTS Service: lazy-load voices on first use (saves startup RAM) ────
    try:
        from app.services.tts import TTSService
        logger.info("Initializing TTS service (voices lazy-loaded on first request)...")
        ml_models["tts"] = TTSService()
        logger.info("TTS service initialized (no voices loaded yet).")
    except Exception as e:
        logger.warning(f"TTS service unavailable: {e}")

    logger.info("All services ready. Echo backend is online.")

    yield

    # ── Shutdown ───────────────────────────────────────────────
    logger.info("Shutting down Echo backend and cleaning up resources...")
    ml_models.clear()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Echo — Real-time multilingual speech translation backend for ESP32.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS configuration ─────────────────────────────────────────
origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
if not origins or "*" in origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Health & root endpoints ────────────────────────────────────
@app.get("/", status_code=200)
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint returning service status."""
    logger.info("Health check endpoint called.")
    return {"status": "ok"}


# ── API routers ────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
