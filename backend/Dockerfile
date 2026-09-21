# ============================================================================
# Stage 1: builder
# Installs all Python dependencies into a clean prefix.
# Keeps the final image free from build tools (gcc, curl, etc.).
# ============================================================================
FROM python:3.11-slim AS builder

# --- Environment ---------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=200 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

# --- System build deps ---------------------------------------------------
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Install Poetry ------------------------------------------------------
RUN curl -sSL https://install.python-poetry.org | python3 -

# --- Install Python deps into /usr/local (no venv) -----------------------
WORKDIR /build
COPY pyproject.toml poetry.lock* /build/

# Install only production deps; skip dev/test packages
RUN poetry install --no-root --no-directory --only main 2>/dev/null \
    || poetry install --no-root --no-directory


# ============================================================================
# Stage 2: runtime
# Copies only the installed packages and the app code — no build tools.
# ============================================================================
FROM python:3.11-slim AS runtime

# --- Environment ---------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Model cache dirs — these will be bind-mounted as a Docker volume
    HF_HOME="/model_cache/huggingface" \
    TORCH_HOME="/model_cache/torch" \
    PIPER_CACHE="/model_cache/piper" \
    # Disable Hugging Face Xet CDN (requires auth even for public models)
    HF_HUB_DISABLE_XET=1

# --- Runtime system deps -------------------------------------------------
# ffmpeg  : required by pydub for audio re-sampling
# libgomp : required by faster-whisper / onnxruntime (OpenMP)
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ffmpeg \
        libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Copy installed Python packages from builder -------------------------
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# --- Copy application code -----------------------------------------------
WORKDIR /app
COPY . /app/

# --- Model cache volume mount point --------------------------------------
# AI models are NOT baked into the image (they are 2-10 GB).
# They are downloaded at first startup and cached in this volume.
# On subsequent container restarts the volume already contains the models.
VOLUME ["/model_cache"]

# --- Upload directory mount point ----------------------------------------
# Audio files uploaded from ESP32 or via REST are persisted here.
VOLUME ["/app/audio_uploads"]

# --- Non-root user for security ------------------------------------------
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app
USER appuser

# --- Port ----------------------------------------------------------------
EXPOSE 8000

# --- Healthcheck ---------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# --- Entrypoint ----------------------------------------------------------
# Production: no --reload, workers=1 (single process, models in memory)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
