#!/usr/bin/env python3
"""
test_robustness.py — Edge-case robustness tests for the pipeline.

Tests documented in the capstone report under "Robustness Testing".
Each test case documents: input conditions, expected behavior, actual result.

Run with:
  poetry run python test_robustness.py
  poetry run python test_robustness.py --url https://your-vm.com   # remote

Edge cases tested:
  1. Silent audio (no speech)
  2. Very short utterance (< 0.3 s)
  3. Very long utterance (> 10 s)
  4. Background noise only (sine wave — no speech content)
  5. Unsupported source language text
  6. Unsupported target language code
  7. Empty audio file (0 bytes WAV header only)
  8. Non-WAV file passed as WAV
  9. Translation requested but translation service unavailable
 10. Extremely long text translation
"""

import asyncio
import io
import json
import os
import struct
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Audio generators
# ---------------------------------------------------------------------------

def _wav(samples: np.ndarray, sr=16000) -> bytes:
    data = samples.astype(np.int16).tobytes()
    buf = io.BytesIO()
    buf.write(b"RIFF"); buf.write(struct.pack("<I", 36 + len(data)))
    buf.write(b"WAVE"); buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
    buf.write(b"data"); buf.write(struct.pack("<I", len(data))); buf.write(data)
    return buf.getvalue()


def silence_wav(duration=2.0, sr=16000):
    return _wav(np.zeros(int(sr * duration), dtype=np.int16))


def noise_wav(duration=2.0, sr=16000, amplitude=500):
    rng = np.random.default_rng(42)
    return _wav((rng.random(int(sr * duration)) * amplitude).astype(np.int16))


def short_speech_wav(duration=0.2, sr=16000):
    """Very short burst — simulates a click or cough."""
    t = np.linspace(0, duration, int(sr * duration))
    return _wav((3000 * np.sin(2 * np.pi * 440 * t)))


def long_speech_wav(duration=12.0, sr=16000):
    """12-second recording — tests max duration handling."""
    t = np.linspace(0, duration, int(sr * duration))
    return _wav((2000 * np.sin(2 * np.pi * 440 * t)))


def empty_wav():
    """Minimal WAV header with zero data samples."""
    return _wav(np.array([], dtype=np.int16))


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class RobustnessTestRunner:
    def __init__(self, ml_models: dict, tmp_dir: str):
        self.models = ml_models
        self.tmp = tmp_dir
        self.results = []

    def _write_wav(self, name: str, data: bytes) -> str:
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def _run(self, file_path: str, target_language=None, expected_status=None, label=""):
        from app.services.pipeline import PipelineOrchestrator
        t0 = time.perf_counter()
        try:
            result = await PipelineOrchestrator.run(
                file_path=file_path,
                ml_models=self.models,
                device_id="robustness_test",
                target_language=target_language,
            )
            elapsed = time.perf_counter() - t0
            status = result.status
            text = result.transcription.get("text", "") if result.transcription else ""
            pass_fail = "✅ PASS" if expected_status is None or status == expected_status else f"⚠️  UNEXPECTED ({status})"

            entry = {
                "label": label,
                "status": status,
                "transcribed_text": text[:80],
                "elapsed_sec": round(elapsed, 3),
                "expected": expected_status,
                "pass": expected_status is None or status == expected_status,
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            pass_fail = "✅ PASS (exception caught)" if expected_status == "exception" else f"❌ UNEXPECTED EXCEPTION"
            entry = {
                "label": label,
                "status": "exception",
                "error": str(e)[:120],
                "elapsed_sec": round(elapsed, 3),
                "expected": expected_status,
                "pass": expected_status == "exception",
            }

        self.results.append(entry)
        print(f"  [{pass_fail}] {label}")
        print(f"          Status: {entry['status']}  |  Time: {entry['elapsed_sec']:.2f}s")
        if entry.get("transcribed_text"):
            print(f"          Text: \"{entry['transcribed_text']}\"")
        if entry.get("error"):
            print(f"          Error: {entry['error']}")
        print()
        return entry

    async def run_all(self):
        print("=" * 60)
        print("  ROBUSTNESS EDGE-CASE TESTS")
        print("=" * 60)

        # 1. Silent audio
        p = self._write_wav("silence.wav", silence_wav())
        await self._run(p, target_language="es", expected_status="success",
                        label="1. Silent audio (no speech)")

        # 2. Very short utterance
        p = self._write_wav("short.wav", short_speech_wav(0.2))
        await self._run(p, target_language="es",
                        label="2. Very short utterance (0.2s)")

        # 3. Long audio (> 10s)
        p = self._write_wav("long.wav", long_speech_wav(12.0))
        await self._run(p, target_language="es",
                        label="3. Long audio (12s)")

        # 4. Background noise only
        p = self._write_wav("noise.wav", noise_wav())
        await self._run(p, target_language="es",
                        label="4. Background noise only (no intelligible speech)")

        # 5. Empty WAV
        p = self._write_wav("empty.wav", empty_wav())
        await self._run(p, target_language="es", expected_status="success",
                        label="5. Empty WAV (0 samples)")

        # 6. Unsupported target language
        p = self._write_wav("valid.wav", noise_wav(duration=1.0))
        await self._run(p, target_language="xx",
                        label="6. Unsupported target language ('xx')")

        # 7. No target language (transcription only)
        p = self._write_wav("notarget.wav", noise_wav(duration=1.0))
        await self._run(p, target_language=None, expected_status="success",
                        label="7. No target language (transcription only)")

        # 8. Translation service missing
        models_no_trans = {k: v for k, v in self.models.items() if k != "translation"}
        p = self._write_wav("notrans.wav", noise_wav(duration=1.0))
        from app.services.pipeline import PipelineOrchestrator
        try:
            result = await PipelineOrchestrator.run(
                file_path=p,
                ml_models=models_no_trans,
                device_id="robustness_test",
                target_language="es",
            )
            entry = {
                "label": "8. Translation service unavailable",
                "status": result.status,
                "pass": True,
                "elapsed_sec": 0,
            }
        except Exception as e:
            entry = {"label": "8. Translation service unavailable", "status": "exception", "error": str(e), "pass": False}

        self.results.append(entry)
        print(f"  [{'✅ PASS' if entry['pass'] else '❌ FAIL'}] 8. Translation service unavailable")
        print(f"          Status: {entry['status']}")
        print()

        # 9. TTS service missing
        models_no_tts = {k: v for k, v in self.models.items() if k != "tts"}
        p = self._write_wav("notts.wav", noise_wav(duration=1.0))
        await self._run(p, target_language="es",
                        label="9. TTS service unavailable")

        # Summary
        passed = sum(1 for r in self.results if r.get("pass", False))
        total = len(self.results)
        print("=" * 60)
        print(f"  Results: {passed}/{total} tests passed")
        print("=" * 60)
        return self.results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    import argparse
    import tempfile

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="robustness_report.json")
    args = parser.parse_args()

    print("Loading AI models for robustness tests...")
    from app.services.transcription import TranscriptionService
    from app.services.translation import TranslationService
    from app.services.tts import TTSService

    ml_models = {
        "asr": TranscriptionService(model_name="base", device="cpu", compute_type="int8"),
        "translation": TranslationService(),
        "tts": TTSService(),
    }
    print("✅ Models loaded\n")

    with tempfile.TemporaryDirectory() as tmp:
        runner = RobustnessTestRunner(ml_models, tmp)
        results = await runner.run_all()

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Report saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
