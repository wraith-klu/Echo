# Learning 5 — Translation Engine: NLLB-200 on CPU

## What We Built

**Step 5** of the real-time speech translation backend adds the multilingual translation engine. After audio is transcribed (Whisper) and the source language is detected (LID), the text is now translated into any supported target language using Meta's **NLLB-200** ("No Language Left Behind") model.

---

## Why NLLB-200?

We evaluated three major options:

| Model | Languages | Size (FP32) | CPU Speed | Notes |
|---|---|---|---|---|
| **NLLB-200-distilled-600M** | 200+ | ~2.4 GB | Medium | Best for our constraints |
| MarianMT | ~150 pairs | ~300 MB/pair | Fast | One model per pair; impractical at scale |
| mBART-50 | 50 | ~2.4 GB | Slow | Fewer languages, not seq2seq-ready out-of-box |

**We chose `facebook/nllb-200-distilled-600M`** because:

- **One model, 200 languages** — single download, zero routing logic
- **Distilled 600M** is the sweet spot: smaller than the 1.3B and 3.3B variants, but significantly higher quality than tiny bilingual models
- **Supported by `transformers`** out-of-the-box: tokenizer, model, and `lang_code_to_id` are all standardized

---

## Dynamic Quantization (int8)

Loading NLLB in `float32` uses ~2.4 GB RAM. On our Oracle Cloud CPU VM this is tight. We apply **PyTorch dynamic quantization** immediately after loading:

```python
model = torch.quantization.quantize_dynamic(
    raw_model,
    {torch.nn.Linear},  # only quantize Linear layers
    dtype=torch.qint8,
)
```

**Effect:**
- RAM drops from ~2.4 GB → ~1.2 GB
- CPU inference is 2–3× faster
- BLEU quality loss is negligible (< 0.5 BLEU on most pairs)

This is **dynamic** (not static) quantization, meaning weights are quantized offline but activations are computed at full precision. No calibration dataset is needed.

---

## Language Codes: NLLB Format

NLLB does not use ISO 639-1 (`en`, `es`) directly. It uses its own BCP-47 style codes:

| ISO 639-1 | NLLB Code |
|---|---|
| `en` | `eng_Latn` |
| `es` | `spa_Latn` |
| `fr` | `fra_Latn` |
| `de` | `deu_Latn` |
| `it` | `ita_Latn` |
| `pt` | `por_Latn` |
| `zh` | `zho_Hans` |
| `ja` | `jpn_Jpan` |
| `ko` | `kor_Hang` |
| `ru` | `rus_Cyrl` |

The mapping is maintained in `NLLB_LANG_MAP` in `translation.py` and is the single source of truth for both REST and WebSocket validation.

---

## How Translation Is Triggered

### REST API (`POST /api/v1/audio/transcribe`)

Add `target_language` as a form field:

```
POST /api/v1/audio/transcribe
  file=<audio>
  source_language=en    (optional override)
  target_language=es    (optional; omit to skip translation)
```

**Response shape with translation:**
```json
{
  "status": "success",
  "filename": "...",
  "transcription": {
    "text": "Hello, how are you?",
    "language_detection": { "detected_language": "en", "confidence": 0.98 }
  },
  "translation": {
    "translated_text": "Hola, ¿cómo estás?",
    "source_lang": "en",
    "target_lang": "es",
    "source_nllb": "eng_Latn",
    "target_nllb": "spa_Latn",
    "latency_sec": 1.23
  }
}
```

If `target_language` is omitted, the `"translation"` key is absent entirely.

---

### WebSocket (`/ws/audio`)

#### Via query parameter (at connect time):
```
ws://host/ws/audio?device_id=ESP32&target_language=fr
```

#### Via JSON command (mid-session, no reconnect needed):
```json
{ "command": "set_target_language", "language": "de" }
{ "command": "clear_target_language" }
```

**Each audio segment reply now optionally includes:**
```json
{
  "status": "segment_saved",
  "transcription": { ... },
  "translation": {
    "translated_text": "Bonjour, comment allez-vous?",
    "latency_sec": 1.45
  }
}
```

---

## Model Lifecycle

The model is a **singleton** loaded once at FastAPI startup:

```
lifespan startup
  └── TranscriptionService  (Whisper, int8 CTranslate2)
  └── TranslationService    (NLLB, int8 PyTorch dynamic quantization)
```

Both services are stored in `ml_models["asr"]` and `ml_models["translation"]` and accessed by all request handlers without reloading.

---

## Error Handling

| Situation | Behaviour |
|---|---|
| `target_language` not in `NLLB_LANG_MAP` | HTTP 400 / WebSocket error JSON |
| Translation model not yet loaded (startup race) | HTTP 503 / silent skip in WebSocket |
| Translation model raises ValueError (empty text) | HTTP 400 / WebSocket error with message |
| Any unexpected exception | HTTP 500 / WebSocket error JSON |
| Source lang == target lang | Instant no-op; returns original text with latency_sec: 0.0 |

---

## Performance Notes

Running on a 4-core Oracle Cloud CPU VM:

| Utterance Length | Approximate Latency |
|---|---|
| Short (< 10 words) | 0.8 – 1.5 s |
| Medium (10–30 words) | 1.5 – 3.5 s |
| Long (30–80 words) | 3.5 – 8 s |

Beam search (`num_beams=4`) is used for quality. For lower latency you can reduce to `num_beams=1` (greedy decoding) at the cost of some output quality.

---

## Files Changed in This Step

| File | Change |
|---|---|
| `app/services/translation.py` | NEW — TranslationService with NLLB + dynamic quantization |
| `app/main.py` | Added TranslationService import + startup loading in lifespan |
| `app/api/v1/endpoints.py` | Added target_language Form param + translation call in REST handler |
| `app/api/v1/websocket.py` | Added target_language query param, set/clear_target_language commands, translation call |
| `test_translation.py` | NEW — 8-case standalone test suite |
| `.env` | Added HF_HUB_DISABLE_XET=1, updated TRANSLATION_MODEL_NAME |
| `pyproject.toml` | torch, transformers, sentencepiece added (Step 4b) |

---

## Gotcha: Hugging Face Xet Storage (Important for Deployment)

### What happened

When trying to download `facebook/nllb-200-distilled-600M` via `AutoModelForSeq2SeqLM.from_pretrained()`, the download stalled silently at 0 bytes. Two separate bugs were found:

**Bug 1 — Wrong filename:** Newer `transformers` defaults to requesting `model.safetensors` first. This model only has `pytorch_model.bin`. The library silently got a 404 and appeared to hang.

**Fix:** Pass `use_safetensors=False` to `from_pretrained()`.

```python
raw_model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME,
    use_safetensors=False,   # repo only has pytorch_model.bin
)
```

**Bug 2 — Xet Storage CDN requires authentication:** HF recently migrated large files to their new "Xet Storage" CDN. Even for public models, the Xet client requests a read-token via:
```
GET /api/models/{repo}/xet-read-token/{commit}
```
When unauthenticated, the token request stalls/returns empty and the download writes 0 bytes indefinitely with no error or timeout.

**Fix 1:** Set `HF_HUB_DISABLE_XET=1` env var — forces `huggingface_hub` to use the classic CDN (AWS CloudFront) instead.

**Fix 2 (alternative):** Log in with `huggingface-cli login` using a free HF account token.

### Where the fix is applied

```python
# app/services/translation.py — applied at import time
import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
```

```ini
# .env — applied for server startup
HF_HUB_DISABLE_XET=1
```

### Oracle Cloud deployment note

On your Oracle Cloud VM, set this in the systemd service file or `.env` before first startup:
```ini
Environment="HF_HUB_DISABLE_XET=1"
```
Otherwise the first model download will stall silently and the server will appear to hang indefinitely at startup.

---

## Next Steps

- **Step 6: TTS (Text-to-Speech)** — convert translated text back to audio (e.g., using `edge-tts` or `coqui-tts`)
- **Step 7: WebSocket full roundtrip** — end-to-end: PCM in → translated audio out
- **Streaming translation** — consider chunked generation for lower time-to-first-token latency on long sentences
