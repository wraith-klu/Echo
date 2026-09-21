# Speech Translation Backend

A modular FastAPI backend scaffolding for a real-time multilingual speech translation system. It is designed to stream audio from an IoT device (ESP32-S3) over WebSockets and process it through ASR, Translation, and TTS pipelines.

## Project Structure

```
p:/CapsTron Project - 1/backend
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI application initialization & middleware config
│   ├── config.py           # Configuration settings (Pydantic settings)
│   ├── api/                # API router components
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py   # Version 1 root router mounting endpoints
│   │       ├── endpoints.py # Health, basic GET/POST endpoints
│   │       └── websocket.py # WebSocket handling for audio streaming
│   ├── services/           # Speech pipeline logic
│   │   ├── __init__.py
│   │   ├── ingestion.py    # Raw audio buffering and chunking from ESP32
│   │   ├── asr.py          # Speech-to-Text inference wrapper (faster-whisper)
│   │   ├── translation.py  # Machine translation service (e.g., MarianMT)
│   │   └── tts.py          # Text-to-Speech generation
│   ├── models/             # Database models (SQLAlchemy/SQLModel)
│   │   ├── __init__.py
│   │   └── db.py
│   └── core/               # Shared utilities (logging, authentication)
│       ├── __init__.py
│       └── logger.py
├── .env.example            # Reference environment variables
├── .gitignore              # Python/Docker gitignore rules
├── Dockerfile              # Container definition for FastAPI backend
├── pyproject.toml          # Poetry dependency management file
└── learning1.md            # Technical interview reference guide
```

---

## Getting Started

### Prerequisites

Ensure you have one of the following installed:
- [Poetry](https://python-poetry.org/docs/) (Recommended)
- Python 3.11+
- [Docker](https://www.docker.com/) and Docker Compose

---

## Local Setup & Run

### Option 1: Using Poetry (Recommended)

1. **Install dependencies and create virtual environment:**
   ```bash
   poetry install
   ```

2. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Option 2: Using standard `venv` and `pip`

If you prefer `pip`, you can generate `requirements.txt` from Poetry or install direct packages:

1. **Create and activate venv:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install core dependencies:**
   ```bash
   pip install fastapi uvicorn[standard] python-multipart websockets python-dotenv pydantic-settings
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Running with Docker Compose

1. **Build and start the container:**
   ```bash
   docker compose up --build -d
   ```

2. **Check container logs:**
   ```bash
   docker compose logs -f
   ```

3. **Stop the container:**
   ```bash
   docker compose down
   ```

---

## Verifying the Setup

To verify that the server is active, test the `/health` endpoint using curl:

### Health Check Request:
```bash
curl http://localhost:8000/health
```

### Expected Response:
```json
{"status":"ok"}
```

You can also test the versioned api status:
```bash
curl http://localhost:8000/api/v1/status
```

Interactive documentation is available at `http://localhost:8000/docs`.
