# ============================================================================
# Stage 1: builder
# Installs all Python dependencies into a clean prefix.
# Keeps the final image free from build tools (gcc, curl, etc.).
# NOTE: torch/transformers removed — translation uses Gemini Flash API instead.
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
    # Piper TTS & HF model cache (will download on first request, not at startup)
    HF_HOME="/tmp/huggingface" \
    PIPER_CACHE="/tmp/piper" \
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

# --- Create writable dirs for runtime cache & uploads -------------------
# On Render free tier there is no persistent disk; models re-download on each
# cold start. The /tmp directory is always writable even as non-root.
RUN mkdir -p /tmp/huggingface /tmp/piper /app/audio_uploads \
    && addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

# --- Port ----------------------------------------------------------------
EXPOSE 8000

# --- Healthcheck ---------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# --- Entrypoint ----------------------------------------------------------
# Dynamic $PORT support for Render (defaults to 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"]
