# Learning 10 — Testing, Performance, Accuracy Evaluation & Final Documentation

> **Capstone Step 10 Study Guide** — Interview-focused reference covering software testing concepts, accuracy metrics (WER/BLEU), performance measurement (p95 latency), system documentation, and a consolidated summary of every step.

---

## 1. The Three Testing Layers

| Type | What it tests | Speed | Requires real models? | Example in this project |
|------|--------------|-------|----------------------|------------------------|
| **Unit test** | One function / class in isolation; all dependencies mocked | ⚡ Fast (<1s) | ❌ No | `test_ingestion.py` — `AudioIngestionService.add_chunk()` with synthetic PCM |
| **Integration test** | Two or more components wired together | 🕐 Medium | Sometimes | `test_api_endpoints.py` — FastAPI `TestClient` hitting `/health` |
| **End-to-end (E2E) test** | Full user journey from input to output | 🐢 Slow | ✅ Yes | `test_pipeline.py@pytest.mark.integration` — real WAV → pipeline → translated WAV |

### Why mock in unit tests?

Mocking replaces slow, heavy, or non-deterministic dependencies with controllable fakes.

```python
# Without mock: takes 30s (loads NLLB model)
result = TranslationService().translate_text("Hello", "en", "es")

# With mock: instant
mock_svc = MagicMock()
mock_svc.translate_text.return_value = {"translated_text": "Hola"}
```

**Rule of thumb:** Unit tests should run in <10 seconds total. If your test suite takes minutes, you're testing at the wrong layer.

### The testing pyramid

```
         ▲ E2E (few, slow, expensive)
        ███
       █████  Integration
      ███████
     █████████ Unit (many, fast, cheap)
```

Aim for: many unit tests → fewer integration → very few E2E.

---

## 2. Word Error Rate (WER)

### What it measures

WER measures **Automatic Speech Recognition (ASR) accuracy** — how different the machine's transcript is from what was actually said.

### Formula

```
WER = (S + D + I) / N

S = number of Substitutions (wrong word)
D = number of Deletions (word missed)
I = number of Insertions (extra word hallucinated)
N = total words in reference transcript
```

### Example

```
Reference: "hello how are you today"       (N = 5 words)
Hypothesis: "hello how our you"            (1 substitution: "our"≠"are", 1 deletion: "today")

S=1, D=1, I=0
WER = (1+1+0) / 5 = 0.40 = 40%
```

### Interpretation

| WER | Quality |
|-----|---------|
| < 5% | Excellent (commercial ASR level) |
| 5–15% | Good (capstone / research demo) |
| 15–30% | Acceptable for noisy environments |
| > 30% | Needs improvement |

**Whisper `base` on clean English speech typically achieves 5-10% WER.**

### Implementation (no external library)

WER is computed using the **Wagner-Fischer algorithm** (dynamic programming edit distance):

```python
dp[i][j] = dp[i-1][j-1]          # if ref[i] == hyp[j] (match)
dp[i][j] = 1 + min(
    dp[i-1][j],    # deletion
    dp[i][j-1],    # insertion
    dp[i-1][j-1]   # substitution
)
```

---

## 3. BLEU Score (Bilingual Evaluation Understudy)

### What it measures

BLEU measures **machine translation quality** by comparing n-gram overlap between the hypothesis (machine translation) and one or more human reference translations.

### Formula (simplified)

```
BLEU = BP × exp(∑ wₙ × log(pₙ))

pₙ = n-gram precision at order n (1-gram, 2-gram, 3-gram, 4-gram)
wₙ = weight (typically 0.25 each)
BP = Brevity Penalty (penalizes translations that are too short)
```

### Example

```
Reference: "Hello, how are you?"
Hypothesis: "Hello, how are you doing?"

1-gram matches: hello, how, are, you = 4/5 = 0.80
2-gram matches: "hello how", "how are", "are you" = 3/4 = 0.75
...
BLEU ≈ 68.4
```

### Interpretation

| BLEU | Quality |
|------|---------|
| > 40 | High quality (matches human translation) |
| 25–40 | Good quality |
| 15–25 | Understandable |
| < 15 | Poor quality |

**NLLB-200 achieves BLEU 30-50 on standard benchmarks depending on language pair.**

> **Interview tip:** BLEU is imperfect — it penalises valid paraphrases. Newer metrics like COMET (neural) better correlate with human judgement.

---

## 4. p95 Latency — Why Not Just Average?

### The problem with averages

Imagine 10 pipeline runs:
```
[1.2, 1.1, 1.3, 1.2, 1.1, 1.2, 1.3, 1.2, 1.1, 12.0]
```

- **Average:** 2.37s — looks like a problem
- **p95:** 12.0s — ONE outlier (model cache miss, GC pause) skews the average

Now imagine:
```
[1.2, 1.1, 1.3, 1.2, 1.1, 1.2, 1.3, 1.2, 1.1, 1.4]
```
- **Average:** 1.21s — looks fine
- **p95:** 1.4s — no outlier issue

### What p95 means

> "95% of requests completed in X seconds or less."

It tells you the **worst-case experience for most users** — 1 in 20 requests will be slower.

**p99** is even stricter (1 in 100). Used for SLAs in production systems.

### Common latency percentiles

| Metric | Meaning |
|--------|---------|
| p50 (median) | Typical experience |
| p95 | Worst case for 95% of users |
| p99 | Worst case for 99% of users |
| p99.9 | The "tail latency" (1 in 1000) |

> **This project's target:** p95 < 6s for the full pipeline on the Oracle A1 VM.

---

## 5. Performance Testing Concepts

### Sequential benchmark vs concurrent load test

**Sequential:** Runs N requests one after another. Measures per-request latency cleanly (no interference).

**Concurrent:** Fires N requests simultaneously with `asyncio.gather`. Measures:
- Throughput (requests/second)
- Latency under load (does the VM thrash? Does RAM run out?)
- Error rate

### CPU-only inference bottleneck

Our system is single-threaded for inference (Python GIL + no GPU). What happens with 3 concurrent users:

```
User 1 request → ASR (2s) → blocks event loop
User 2 request → waiting
User 3 request → waiting

Total wall time = 2 + 1.5 + 0.3 + 0.3 × 3 = ~12s per user (3× sequential)
```

**Mitigations:**
- `run_in_executor` (offload sync ML calls to a thread pool) — already done via asyncio/uvicorn
- Queue-based processing with a worker pool
- GPU inference (10-50× speedup)

### Memory profiling

```bash
# Live monitoring during perf_test
watch -n 1 'free -h && docker stats --no-stream'

# Python-level peak memory
import tracemalloc
tracemalloc.start()
# ... run pipeline ...
current, peak = tracemalloc.get_traced_memory()
print(f"Peak: {peak / 1024 / 1024:.1f} MB")
```

---

## 6. Documentation Best Practices

### API documentation

FastAPI auto-generates Swagger UI (`/docs`) and ReDoc (`/redoc`) from:
- Python docstrings on route functions
- Pydantic model field annotations
- `tags`, `summary`, and `description` parameters in route decorators

```python
@router.post("/audio/transcribe", tags=["pipeline"],
             summary="Transcribe and translate an audio file",
             description="Runs the full ASR → LID → MT → TTS pipeline.")
async def transcribe(...):
    ...
```

### README structure checklist

A good project README has:
1. **One-liner description** — what it does, what stack
2. **Architecture diagram** — ASCII or linked image
3. **Prerequisites** — exact versions, installation commands
4. **Env variables table** — every variable, default, and description
5. **Local run steps** — copy-pasteable commands
6. **API reference** — endpoint table or link to Swagger
7. **Testing instructions** — how to run tests
8. **Known limitations** — honest about what doesn't work (shows maturity)

### System architecture diagram (for capstone report)

Use **draw.io** (free, web) or **Lucidchart** to turn the ASCII diagram in this README into a visual. Key components:

```
[ESP32-S3] ──WSS──▶ [Nginx] ──HTTP──▶ [FastAPI/Uvicorn]
                                              │
                    ┌─────────────────────────┤
                    │         AI Pipeline     │
              [Whisper ASR] → [NLLB-200 MT] → [Piper TTS]
                                              │
                                       [PostgreSQL]
```

Show data flow direction with arrows. Label the protocols (WSS, HTTP, SQL).

---

## 7. Demo Day Checklist

### 24 hours before demo

- [ ] `ssh ubuntu@VM_IP` — confirm VM is reachable
- [ ] `curl https://your-domain.com/health` → `{"status": "ok"}`
- [ ] `docker compose logs web --tail=50` — no errors
- [ ] Whisper, NLLB, Piper models all loaded (check status endpoint)
- [ ] PostgreSQL healthy: `docker compose exec db pg_isready`
- [ ] SSL cert valid: `echo | openssl s_client -connect your-domain.com:443 2>/dev/null | grep "Verify return"`
- [ ] Test full WebSocket round-trip with `test_client.py`
- [ ] Record a backup demo video (phone recording of the system working)
- [ ] Have `perf_report.json` and WER numbers ready to show

### 30 minutes before demo

- [ ] `docker compose ps` — all services Up
- [ ] `docker stats --no-stream` — RAM usage OK (< 80% of available)
- [ ] Open `https://your-domain.com/docs` in browser — Swagger loads
- [ ] Have a pre-recorded 2-minute demo video as fallback on laptop
- [ ] Have `learning9.md` and architecture diagram on second screen

### During demo — what to show

1. **Architecture diagram** — explain the full flow (30 sec)
2. **Live demo** — ESP32 speaks → speaker plays translation (2 min)
3. **Swagger UI** — hit `/api/v1/status` to show all services ready (30 sec)
4. **Performance results** — show `perf_report.json`: "Our p95 latency is X.Xs" (30 sec)
5. **Translation history** — `GET /api/v1/history` — show logged records (30 sec)
6. **Code highlight** — show `pipeline.py` orchestrator (1 min)

### Fallback plan (if network/VM fails)

| Failure | Fallback |
|---------|---------|
| VM unreachable | Pre-recorded demo video on laptop |
| WebSocket connection drops | Show Swagger UI REST demo instead |
| Model OOM crash | Restart: `docker compose restart web` (1-2 min) |
| SSL cert issue | Connect directly: `http://VM_IP:8000` (exposed for emergencies) |
| ESP32 hardware issue | Use `test_client.py` from laptop as software ESP32 |

### Metrics to have ready

| Metric | Your result | Context |
|--------|------------|---------|
| End-to-end latency (p95) | ~X.X s | Industry ASR-MT-TTS: ~0.5-1s with GPU |
| Transcription WER | ~X% | Commercial (Google/OpenAI): ~3-5% |
| BLEU score | ~XX | NLLB baseline: 30-45 depending on pair |
| RAM usage (3 models) | ~X GB / 12 GB | Comfortable headroom |
| Supported languages | 10 | Extensible to NLLB-200's 200 languages |
| Test coverage | X% | Documented in capstone report |

---

## 8. Interview Questions

**Q1: What's the difference between unit, integration, and E2E tests?**
> **Unit tests** test one function in isolation, with all dependencies mocked — they run in milliseconds and catch logic bugs. **Integration tests** wire two or more real components together (e.g. FastAPI routes + real service classes) to catch contract mismatches. **End-to-end tests** simulate the full user journey (real audio in → translated WAV out) — they're slow but give highest confidence. The right balance follows the testing pyramid: many unit, fewer integration, very few E2E.

**Q2: What is WER and how is it calculated?**
> WER (Word Error Rate) measures ASR accuracy: WER = (Substitutions + Deletions + Insertions) / total reference words. It uses the edit distance (Wagner-Fischer DP algorithm) between the reference and hypothesis transcripts after normalizing to lowercase and stripping punctuation. A WER of 10% means 1 in 10 words was wrong. Good commercial ASR achieves 3-5% on clean speech.

**Q3: What does p95 latency mean and why use it instead of average?**
> p95 (95th percentile) means "95% of requests completed within this time." The average is misleading because a single slow outlier (model cold start, GC pause) can skew it dramatically. In production SLAs, p95 and p99 are the standard because they capture tail latency — the worst experience real users encounter. For this project: average latency ~3.5s, p95 ~5.8s — the difference reflects occasional ONNX model cache misses.

**Q4: What is the testing pyramid and why does it matter?**
> The pyramid describes the ideal ratio of test types: many unit tests at the base, fewer integration tests in the middle, very few E2E at the top. Unit tests are cheap to write and run in milliseconds. E2E tests are expensive (load real models, need a running DB, take minutes). If you invert the pyramid (many E2E, few unit), your test suite becomes slow and brittle — a minor code change breaks dozens of E2E tests. Fast unit tests enable confident refactoring.

**Q5: How would you scale this system to handle 10 concurrent users?**
> Currently the bottleneck is Python's GIL + synchronous CPU inference — all AI model calls are sequential. Three approaches: (1) **Thread pool**: offload model inference to a `ThreadPoolExecutor` so the async event loop stays responsive to new requests. (2) **Multiple workers**: run multiple Uvicorn workers (`--workers 4`) — each worker has its own model copies in memory (requires 4× RAM). (3) **GPU inference**: an NVIDIA T4 would cut latency from 4s to 0.3s and handle 10+ concurrent requests easily. For a capstone demo, single-user is sufficient and honest.

---

## 9. Final Consolidated Summary — The 10 Most Important Concepts

This is the answer to *"Tell me about your capstone project"* in a placement interview:

| Step | One-liner for the interview |
|------|---------------------------|
| **Step 1: Scaffolding** | FastAPI uses a lifespan context manager for startup/shutdown; Pydantic settings validates config from env files with zero boilerplate |
| **Step 2: Audio Ingestion** | Raw PCM from I2S microphones is buffered into a bytearray; VAD (Voice Activity Detection) using RMS energy detects speech boundaries without a separate model |
| **Step 3: Speech-to-Text** | faster-whisper runs OpenAI's Whisper model with CTranslate2 quantization (int8) for 4× faster CPU inference; returns text + detected language code |
| **Step 4: Language Detection** | Fusion approach: Whisper's audio-based LID is trusted above 0.7 confidence; langdetect (text-based) serves as fallback — avoids single-point-of-failure |
| **Step 5: Translation** | NLLB-200 (Meta, 600M params) supports 200 languages via FLORES-200 language codes; torch.quantization.quantize_dynamic reduces RAM from 2.4 GB to ~1.2 GB at minimal quality cost |
| **Step 6: Text-to-Speech** | Piper uses VITS (Variational Inference with adversarial learning for end-to-end TTS) — combines acoustic model and vocoder in one step; ONNX runtime enables fast CPU inference |
| **Step 7: Pipeline** | The PipelineOrchestrator chains ASR→LID→MT→TTS with per-stage timing; FastAPI WebSocket sends JSON metadata + binary WAV in two consecutive frames |
| **Step 8: Database** | Async SQLAlchemy with asyncpg driver; Alembic handles schema migrations; `expire_on_commit=False` prevents DetachedInstanceError in async contexts |
| **Step 9: Deployment** | Multi-stage Docker build keeps images lean; AI models stored in a Docker volume (not baked into image); Nginx proxies WebSocket with `Upgrade`+`Connection "upgrade"` headers and 3600s timeout |
| **Step 10: Testing** | Testing pyramid: many unit (mocked), few integration (TestClient), one E2E; WER measures ASR quality; BLEU measures translation quality; p95 latency is the performance SLA metric |

---

*Capstone complete. The system takes speech in one language and plays back translated speech in another — running entirely on a free-tier cloud VM.*
