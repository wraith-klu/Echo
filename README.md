# Echo — Real-Time Multilingual Speech Translation System

> Backend service for an ESP32-based IoT device that captures speech, translates it in real-time, and plays back translated audio through a speaker.

**Stack:** FastAPI · Python 3.11 · faster-whisper · NLLB-200 · Piper TTS · PostgreSQL · SQLAlchemy · Docker · Nginx

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         ESP32-S3 Device                         │
│  INMP441 Mic → I2S → WebSocket Client → MAX98357A I2S Speaker  │
└────────────────────────┬────────────────────────────────────────┘
                         │  WSS (port 443) — binary PCM chunks
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle Cloud VM (ARM A1)                      │
│                                                                 │
│  ┌────────────┐    ┌──────────────────────────────────────────┐ │
│  │   Nginx    │───▶│           FastAPI + Uvicorn              │ │
│  │ (HTTPS/WSS)│    │                                          │ │
│  └────────────┘    │  ┌────────┐ ┌─────────┐ ┌────────────┐ │ │
│                    │  │Whisper │ │ NLLB-200│ │ Piper TTS  │ │ │
│                    │  │  ASR   │→│ (MT)    │→│ (ONNX)     │ │ │
│                    │  └────────┘ └─────────┘ └────────────┘ │ │
│                    └──────────────────┬───────────────────────┘ │
│                                       │                          │
│                    ┌──────────────────▼───────────────────────┐ │
│                    │        PostgreSQL 15 (Docker)             │ │
│                    │  devices / sessions / translations        │ │
│                    └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │  WAV binary frame (WebSocket response)
                         ▼
                    ESP32 Speaker plays translated audio
```

### Pipeline Flow (per utterance)

```text
Audio chunk received → Voice Activity Detection (VAD)
  → Speech boundary detected
    → Whisper ASR (transcription + language detection)
      → NLLB-200 Machine Translation
        → Piper TTS (synthesize translated speech)
          → WAV binary frame sent back to ESP32
            → PostgreSQL: log translation record
```

---

## Repository Structure

```text
CapsTron Project - 1/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan (model loading)
│   │   ├── config.py            # Pydantic settings (reads .env)
│   │   ├── api/v1/
│   │   │   ├── endpoints.py     # REST: /upload, /transcribe, /history, /devices
│   │   │   ├── websocket.py     # WS: /ws/audio — real-time audio stream
│   │   │   └── router.py
│   │   ├── services/
│   │   │   ├── ingestion.py     # PCM buffering + VAD
│   │   │   ├── transcription.py # faster-whisper wrapper
│   │   │   ├── language_detection.py  # Whisper + langdetect fusion
│   │   │   ├── translation.py   # NLLB-200 (transformers)
│   │   │   ├── tts.py           # Piper TTS (ONNX)
│   │   │   ├── pipeline.py      # PipelineOrchestrator (steps 2-6 in sequence)
│   │   │   └── db_service.py    # Device/session/translation DB helpers
│   │   ├── models/
│   │   │   └── db.py            # SQLAlchemy ORM: Device, User, Session, Translation
│   │   └── core/
│   │       ├── database.py      # Async engine + session factory
│   │       └── logger.py
│   ├── alembic/                 # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── tests/                   # pytest test suite
│   │   ├── conftest.py
│   │   ├── test_ingestion.py
│   │   ├── test_language_detection.py
│   │   ├── test_translation.py
│   │   ├── test_pipeline.py
│   │   ├── test_db_service.py
│   │   └── test_api_endpoints.py
│   ├── perf_test.py             # Latency benchmark + concurrent load test
│   ├── eval_accuracy.py         # WER + BLEU evaluation
│   ├── test_robustness.py       # Edge-case robustness tests
│   ├── Dockerfile               # Multi-stage production Docker build
│   ├── pyproject.toml           # Poetry dependencies
│   ├── pytest.ini
│   ├── .env.example             # Environment variable template
│   └── .env.production.example  # Production secrets template
├── nginx/
│   ├── nginx.conf               # Nginx main config
│   └── conf.d/app.conf          # Virtual host (HTTPS + WebSocket + REST)
├── docker-compose.yml           # Production: web + db + nginx + certbot
├── docker-compose.dev.yml       # Dev override: hot-reload, exposed ports
├── deploy.sh                    # CI/CD-lite deploy script
├── learning1-10.md              # Step-by-step interview study guides
└── README.md                    # This file
```

---

## Prerequisites

- **Python 3.11+** and [Poetry](https://python-poetry.org/)
- **Docker** and **Docker Compose** (for containerized runs)
- **ffmpeg** (required by pydub — `apt install ffmpeg` / `brew install ffmpeg`)
- **PostgreSQL 15** (or use Docker — the compose file includes it)
- At least **8 GB RAM** free for loading all three AI models simultaneously

---

## Environment Variables

Copy the template and fill in values:

```bash
cp backend/.env.example backend/.env
```

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `PROJECT_NAME` | `Speech Translation Backend` | App display name |
| `API_V1_STR` | `/api/v1` | API version prefix |
| `BACKEND_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (use specific domain in prod) |
| `WHISPER_MODEL_NAME` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium` |
| `TRANSLATION_MODEL_NAME` | `facebook/nllb-200-distilled-600M` | HuggingFace model ID |
| `TTS_MODEL_NAME` | `suno/bark-small` | TTS model (informational) |
| `HF_HUB_DISABLE_XET` | `1` | Disable Xet CDN (avoids auth requirement) |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password |
| `POSTGRES_HOST` | `localhost` | DB host (`db` inside Docker) |
| `POSTGRES_PORT` | `5432` | DB port |
| `POSTGRES_DB` | `speech_translation` | Database name |

---

## Local Development Setup

### Option 1: Poetry (recommended)

```bash
# 1. Install dependencies
cd backend
poetry install

# 2. Start PostgreSQL (Docker)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db

# 3. Run database migrations
poetry run alembic upgrade head

# 4. Start the development server (hot-reload)
poetry run uvicorn app.main:app --reload --port 8000
```

### Option 2: Docker Compose (dev mode)

```bash
# Starts: web (hot-reload) + PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The server will be at: [http://localhost:8000](http://localhost:8000)  
Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/health` | Health check → `{"status": "ok"}` |
| `GET` | `/api/v1/status` | Pipeline component status |
| `POST` | `/api/v1/audio/upload` | Upload a WAV file (multipart) |
| `POST` | `/api/v1/audio/transcribe` | Run full ASR→Translation→TTS pipeline |
| `GET` | `/api/v1/audio/tts/{filename}` | Download a generated TTS WAV |
| `GET` | `/api/v1/history` | Paginated translation history |
| `GET` | `/api/v1/devices` | List registered devices |
| `WS` | `/ws/audio` | Real-time WebSocket audio stream |

Full interactive documentation: `/docs` (Swagger UI) or `/redoc` (ReDoc)

### WebSocket Protocol

**Connect:** `wss://your-domain.com/ws/audio?device_id=ESP32_001&target_language=es`

**Client → Server:**

- Binary frames: raw 16-bit PCM audio chunks at 16kHz mono
- JSON control: `{"command": "end_of_speech"}` | `{"command": "set_target_language", "language": "fr"}`

**Server → Client (after speech boundary):**

- Frame 1 (text): JSON with transcription, translation, and latency breakdown
- Frame 2 (binary): WAV audio file of synthesized translated speech

---

## Running Tests

```bash
cd backend

# Fast unit tests only (no models required, ~5-10 seconds)
poetry run pytest -m "not integration"

# All tests including integration (requires models to be downloaded)
ENABLE_INTEGRATION_TESTS=1 poetry run pytest

# With coverage report
poetry run pytest -m "not integration" --cov=app --cov-report=term-missing

# Robustness edge-case tests (requires models)
poetry run python test_robustness.py

# Performance benchmark
poetry run python perf_test.py --audio test_output/test_en.wav --runs 5

# Accuracy evaluation (WER)
poetry run python eval_accuracy.py wer \
    --audio test_output/test_en.wav \
    --ref "hello this is a test of the piper text to speech service"
```

---

## Production Deployment (Oracle Cloud VM)

### One-time setup

```bash
# SSH into VM
ssh -i ~/.ssh/id_ed25519 ubuntu@YOUR_VM_IP

# Clone repo
git clone https://github.com/YOUR_USERNAME/capstron.git ~/capstron
cd ~/capstron

# Create production secrets
cp backend/.env.production.example backend/.env.production
nano backend/.env.production   # fill in POSTGRES_PASSWORD etc.
chmod 600 backend/.env.production

# Configure your domain in nginx
sed -i 's/YOUR_DOMAIN/api.yourdomain.com/g' nginx/conf.d/app.conf

# Open firewall ports
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable

# First start (HTTP only, to get SSL cert)
docker compose up -d db nginx

# Get SSL certificate
docker compose run --rm --profile certbot certbot certonly \
  --webroot --webroot-path /var/www/certbot \
  -d api.yourdomain.com --email you@email.com \
  --agree-tos --non-interactive

# Start full stack (HTTPS now active; first boot downloads models — ~20 min)
docker compose up -d --build

# Run migrations
docker compose run --rm -e POSTGRES_HOST=db web python -m alembic upgrade head
```

### Subsequent deployments

```bash
# From your laptop:
ssh ubuntu@YOUR_VM_IP "cd ~/capstron && ./deploy.sh"
```

---

## Known Limitations and Future Work

### Current Limitations

| Limitation | Impact | Mitigation |
| ---------- | ------ | ---------- |
| **Batch ASR** (not streaming) | ~2-3s transcription delay per utterance | Acceptable for demo; fix with `faster-whisper` streaming mode |
| **Single-user design** | CPU contention with 2+ simultaneous users | Horizontal scaling or GPU inference |
| **CPU-only inference** | NLLB translation adds ~1-1.5s | Quantization (int8) reduces this; GPU would be <0.1s |
| **10 language support** | Limited to en/es/fr/de/it/pt/zh/ja/ko/ru | Extend to NLLB-200's 200 languages via `NLLB_LANG_MAP` |
| **No auth/API keys** | Any device can connect | Add JWT tokens or device API key validation (Step 9.5) |
| **Model cold start** | First boot takes 20-30 min (download), 60-90s (load) | Pre-warm via startup script |
| **No real-time streaming ASR** | Results only available at end of utterance | Integrate Whisper streaming or Vosk |
| **PostgreSQL required** | DB failure stops translation logging | Graceful fallback already implemented; DB is non-blocking |

### Future Work (Capstone Report)

1. **Streaming ASR** — Replace batch Whisper with real-time chunk-by-chunk transcription using `faster-whisper`'s streaming API or OpenAI's Whisper live.
2. **GPU inference** — A single NVIDIA T4 (available on GCP/AWS spot) would cut total latency from ~4s to <0.5s.
3. **Multi-language Piper voices** — Add 50+ language Piper models for richer TTS coverage.
4. **Speaker diarization** — Identify *who* is speaking in multi-party conversations.
5. **Conversation memory** — Pass conversation history to the translation model for contextual consistency.
6. **Mobile companion app** — React Native app to set target language and view translation history.
7. **Edge model on ESP32-S3** — Run a tiny wake-word detector on-device to reduce unnecessary cloud calls.

---

## Supported Languages

| Code | Language | ASR | Translation | TTS |
| ---- | -------- | --- | ----------- | --- |
| `en` | English | ✅ | ✅ | ✅ |
| `es` | Spanish | ✅ | ✅ | ✅ |
| `fr` | French | ✅ | ✅ | ✅ |
| `de` | German | ✅ | ✅ | ✅ |
| `it` | Italian | ✅ | ✅ | ✅ |
| `pt` | Portuguese | ✅ | ✅ | ✅ |
| `zh` | Chinese | ✅ | ✅ | ✅ |
| `ja` | Japanese | ✅ | ✅ | ✅ |
| `ko` | Korean | ✅ | ✅ | ✅ |
| `ru` | Russian | ✅ | ✅ | ✅ |

---

*Built as a capstone project demonstrating real-time IoT ↔ cloud AI integration.*
