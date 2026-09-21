# Learning 11 — Frontend Prototyping: Streamlit Fundamentals & Web App Integration

> **Capstone Step 11 Study Guide** — Interview-focused reference covering Streamlit architecture, frontend paradigms (Streamlit vs React), browser-based audio capture, REST vs WebSocket tradeoffs, and demonstration best practices.

---

## 1. Streamlit Architecture & Execution Model

### Script Re-execution Paradigm

Streamlit uses a **top-to-bottom re-run execution model**. Every time a user interacts with a widget (clicks a button, selects a dropdown option, records audio), Streamlit executes the entire Python script from line 1 to the end.

- **How state is managed**: Because variables reset on every rerun, Streamlit provides a state dictionary called `st.session_state` that persists values across runs.
- **Caching (`st.cache_data` & `st.cache_resource`)**: Slow operations (e.g., fetching data from a database or loading ML models) can be decorated to skip evaluation on subsequent runs if the parameters have not changed.

### Streamlit vs. Traditional Frontend Frameworks (React / Vue)

| Feature | Streamlit | React / Vue |
| ------- | --------- | ----------- |
| **Language** | Pure Python | JavaScript / TypeScript / JSX |
| **State Location** | Server-side python process | Client-side browser runtime (Virtual DOM) |
| **Execution** | Entire file runs top-to-bottom on change | Incremental component-level reconciliation |
| **Development Speed** | 🚀 Extremely Fast (minutes to hours) | 🐢 Moderate (requires routing, build steps, CSS) |
| **Customizability** | Limited to layout grids and markdown/CSS blocks | Unlimited layout, design system integration, UI animations |
| **Deployment** | Runs as a Python application server | Built to static HTML/JS assets served by CDN |

> **Interview tip:** "Streamlit is ideal for internal tools, AI/ML proofs-of-concept, and scientific data portals. However, for large consumer-facing applications needing micro-interactions, rich client-side animations, and strict load optimizations, a React frontend talking to a REST/GraphQL API is the standard."

---

## 2. Browser-Based Audio Recording Mechanics

### Web Audio API & MediaRecorder

Browser audio recording relies on the HTML5 **MediaDevices API** and **MediaRecorder API** running on the client side:

1. **Permission request**: The browser calls `navigator.mediaDevices.getUserMedia({ audio: true })` to request mic access.
2. **Audio Stream Capture**: Audio data is captured from the mic hardware as a `MediaStream` containing continuous raw floats.
3. **Encoding**: The `MediaRecorder` encodes the stream into a compressed or standard container (usually `.webm`, `.ogg`, or raw `.wav`) in chunks.
4. **Blob creation**: Once recording is stopped, the chunks are compiled into a binary `Blob` (Binary Large Object) containing the audio file.
5. **Transit**: In our Streamlit app, native `st.audio_input` captures this client-side audio blob via HTML5/JavaScript, returns the raw bytes to the Python backend, and we send it via an HTTP POST request to FastAPI.

---

## 3. REST vs. WebSocket Communication Trade-offs

| Criterion | REST (HTTP POST) | WebSocket (WS/WSS) |
| --------- | ---------------- | ----------------- |
| **Protocol** | Stateless Request-Response (HTTP/1.1 or HTTP/2) | Stateful, Persistent, Bidirectional TCP Connection |
| **Data flow** | Client requests → Server responds | Both Client & Server send data frames at any time |
| **Overhead** | High (headers, SSL handshake per request) | Low (tiny frame headers after 1-time handshake) |
| **Latency** | Medium (new TCP connection or HTTP connection reuse) | Minimal (instant transmission over open pipe) |
| **Demo Application** | **Recommended**: Simple, reliable, matches single-audio-chunk uploads | Complex (state tracking, reconnection logic) |
| **Production IoT** | ❌ Poor (ESP32 must open/close connections) | **Recommended**: Allows continuous, low-latency audio streaming |

**Why REST is chosen for the Streamlit demo UI:**
Streamlit's execution model is naturally structured around discrete request-response cycles. When the user finishes recording, we have a complete audio file. POSTing this file via a standard REST API is simpler, handles error responses cleanly, and avoids building complex stateful WebSocket management inside a script that reruns constantly.

---

## 4. Known Limitations & Demoware Pitfalls

1. **Double Audio Re-encoding**: The browser encodes audio (often to WebM), then the backend converts it to 16kHz WAV, then Piper TTS outputs WAV. This adds computing overhead.
2. **No Streamed Audio Feed**: Unlike the ESP32 WebSocket which streams continuous chunks, the Streamlit demo is batch-oriented (entire sentence recorded → sent). It does not showcase the low-latency VAD splitting in the same way.
3. **Local vs Deployed VM URLs**: Connecting Streamlit to a remote HTTPS backend requires handling CORS constraints and mixed-content restrictions if the Streamlit app itself runs on HTTP.

---

## 5. Technical Interview Questions

**Q1: How does Streamlit handle state across user interactions if the script runs top-to-bottom on every click?**

> Streamlit resets all local variables on every rerun. To persist data across runs, it provides `st.session_state`, a key-value dictionary that lives in the server session. For example, we can store history lists or authentication states in `st.session_state` to prevent them from wiping when widgets change.

**Q2: Why did you use an HTTP REST endpoint for the Streamlit UI but a WebSocket endpoint for the ESP32 device?**

> The ESP32 is an IoT device that needs to stream audio chunks continuously with sub-second latency, making WebSockets ideal to avoid connection overhead. The Streamlit demo, however, captures audio in the browser as a complete file first. Standard HTTP POST matches this batch-upload workflow perfectly, is stateless, handles standard HTTP errors cleanly, and avoids adding stateful connection-handling code to a Streamlit script that executes top-to-bottom on every widget click.

**Q3: How does the browser transfer recorded audio from the client's microphone to your python script in Streamlit?**

> The browser uses the JavaScript MediaDevices and MediaRecorder APIs to capture microphone input as an audio blob. In Streamlit, the built-in `st.audio_input` component manages this recording, returns the file-like object directly, and enables easy access in our Python script without iframe-based custom components.

**Q4: How does a reverse proxy like Nginx handle both HTTP and WebSocket connections on the same port?**

> Nginx inspects the HTTP headers of incoming requests. Standard REST requests are routed normally to the web app. If Nginx receives a request with the headers `Upgrade: websocket` and `Connection: Upgrade`, it performs a WebSocket handshake and establishes a persistent TCP tunnel, forwarding all raw data frames bidirectionally between the client and backend service without closing the connection.

---

## 6. Steps 1 to 11 Consolidated Summary

A handy guide mapping every step of the Capstone project:

- **Step 1: Scaffolding** — Project layout with FastAPI Lifespan startup/shutdown; Pydantic configuration validation.
- **Step 2: Audio Ingestion** — Buffer raw PCM from I2S mic; detect speech boundaries using RMS-based VAD.
- **Step 3: Speech-to-Text** — `faster-whisper` running dynamic int8 quantization on CPU for fast transcription.
- **Step 4: Language Detection** — Dual-source LID (Whisper probability + langdetect text fallback) for high reliability.
- **Step 5: Translation** — NLLB-200 Many-to-Many Translation model dynamically quantized to reduce memory usage.
- **Step 6: Text-to-Speech** — Piper neural TTS using Variational Inference (VITS) exported to ONNX format.
- **Step 7: Pipeline Orchestrator** — Chaining modules in a timing-aware service; returning double-frame WS packet (JSON then Binary).
- **Step 8: Database Persistence** — PostgreSQL DB mapping devices, sessions, and histories via async SQLAlchemy.
- **Step 9: Cloud Deployment** — Oracle Cloud A1 VM behind Nginx reverse proxy managing SSL and stateful WS Upgrade paths.
- **Step 10: Testing & Verification** — 64 unit/integration tests running with mock ML engines; latency percentiles benchmarked.
- **Step 11: Streamlit Frontend** — Interactive browser UI for recording laptop mic, evaluating latencies, and showing data.
