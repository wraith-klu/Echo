import warnings

# ── Suppress noisy third-party warnings that are non-actionable in this project ──
# pydub: ffmpeg not on PATH (we use soundfile for conversion instead)
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg", category=RuntimeWarning)
# PyTorch: quantize_per_tensor deprecation (internal to torch.ao quantization, not our code)
warnings.filterwarnings("ignore", message="torch.quantize_per_tensor", category=UserWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="torch.ao")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logger import logger
from app.core.database import Base, engine
from app.api.v1.router import api_router
from app.services.transcription import TranscriptionService
from app.services.translation import TranslationService
from app.services.tts import TTSService

# Import models so SQLAlchemy registers them with Base.metadata
import app.models.db  # noqa: F401

# Dictionary to hold resources loaded during startup (e.g. AI models)
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing speech translation backend...")
    logger.info(f"Project name: {settings.PROJECT_NAME}")

    # Create database tables (dev convenience; use Alembic in production)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified / created.")
    except Exception as e:
        logger.warning(
            f"DB unavailable at startup — tables not created. "
            f"Start PostgreSQL or run Docker to enable persistence. Error: {type(e).__name__}"
        )

    
    # Initialize and load Whisper ASR model
    try:
        ml_models["asr"] = TranscriptionService(model_name=settings.WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    except Exception as e:
        logger.error(f"Failed to load ASR Whisper model: {e}", exc_info=True)

    # Initialize and load NLLB-200 Translation model
    try:
        logger.info("Loading NLLB-200 Translation model (this may take a while on first run) ...")
        ml_models["translation"] = TranslationService()
        logger.info("Translation model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load Translation model: {e}", exc_info=True)

    # Initialize and load TTS Service
    try:
        logger.info("Initializing TTS Service (models will lazy-load on demand) ...")
        ml_models["tts"] = TTSService()
        logger.info("TTS Service initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to load TTS Service: {e}", exc_info=True)

    logger.info("Service dependencies initialized successfully.")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down and cleaning up resources...")
    ml_models.clear()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend service for ESP32 real-time speech translation system.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
# Allowing wildcards or configured origins for IoT/Web integrations
origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
if not origins or "*" in origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level status & health check endpoints
@app.get("/", status_code=200)
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", status_code=200)
async def health_check():
    """
    Simple health check endpoint returning service status.
    """
    logger.info("Health check endpoint called.")
    return {"status": "ok"}

# Mount API version 1 routers
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    # Local run script
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
