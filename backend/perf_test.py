#!/usr/bin/env python3
"""
perf_test.py — End-to-end latency benchmark and concurrent load test.

What it does:
  1. Runs the pipeline N times against a test WAV file (sequential)
  2. Computes: min / max / mean / p50 / p95 latency per stage
  3. Runs a small concurrent load test (configurable # of parallel requests)
  4. Monitors peak memory usage during the run
  5. Writes a JSON report to perf_report.json

Usage:
  poetry run python perf_test.py --audio test_output/test_en.wav --runs 5
  poetry run python perf_test.py --audio test_output/test_en.wav --runs 10 --concurrent 3
  poetry run python perf_test.py --url https://your-vm.com --runs 5   # remote mode
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from typing import List, Dict, Any, Optional
import traceback

import httpx
import psutil


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Pipeline latency benchmark")
    p.add_argument("--audio", default="test_output/test_en.wav",
                   help="Path to WAV file to use as input")
    p.add_argument("--runs", type=int, default=5,
                   help="Number of sequential benchmark runs")
    p.add_argument("--concurrent", type=int, default=1,
                   help="Number of concurrent requests per concurrent-load test")
    p.add_argument("--target-language", default="es",
                   help="Target translation language code")
    p.add_argument("--url", default=None,
                   help="Remote backend URL (e.g. https://api.example.com). "
                        "If not set, runs in-process using the local pipeline.")
    p.add_argument("--output", default="perf_report.json",
                   help="Output JSON report filename")
    return p.parse_args()


# ---------------------------------------------------------------------------
# In-process pipeline run (no network)
# ---------------------------------------------------------------------------

async def run_pipeline_local(audio_path: str, target_language: str, ml_models: dict) -> dict:
    """Run one pipeline pass in-process and return latency breakdown."""
    from app.services.pipeline import PipelineOrchestrator

    t0 = time.perf_counter()
    result = await PipelineOrchestrator.run(
        file_path=audio_path,
        ml_models=ml_models,
        device_id="perf_test",
        target_language=target_language,
    )
    wall = time.perf_counter() - t0

    return {
        "status": result.status,
        "wall_sec": round(wall, 4),
        "latencies": result.latencies or {},
        "error": result.error,
    }


# ---------------------------------------------------------------------------
# Remote HTTP pipeline run
# ---------------------------------------------------------------------------

async def run_pipeline_remote(audio_path: str, target_language: str, base_url: str) -> dict:
    """POST the audio file to a remote backend and extract latency from response."""
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(audio_path, "rb") as f:
            resp = await client.post(
                f"{base_url}/api/v1/audio/transcribe",
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"target_language": target_language},
            )
    wall = time.perf_counter() - t0

    if resp.status_code != 200:
        return {"status": "error", "wall_sec": round(wall, 4), "error": resp.text, "latencies": {}}

    data = resp.json()
    return {
        "status": data.get("status", "unknown"),
        "wall_sec": round(wall, 4),
        "latencies": data.get("latencies", {}),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def percentile(data: List[float], p: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def compute_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(statistics.mean(values), 4),
        "p50": round(percentile(values, 50), 4),
        "p95": round(percentile(values, 95), 4),
        "stddev": round(statistics.stdev(values) if len(values) > 1 else 0.0, 4),
    }


# ---------------------------------------------------------------------------
# Memory snapshot
# ---------------------------------------------------------------------------

def memory_mb() -> float:
    proc = psutil.Process(os.getpid())
    return round(proc.memory_info().rss / 1024 / 1024, 1)


# ---------------------------------------------------------------------------
# Sequential benchmark
# ---------------------------------------------------------------------------

async def run_sequential_benchmark(runner, runs: int) -> List[dict]:
    results = []
    for i in range(runs):
        print(f"  Run {i + 1}/{runs} ... ", end="", flush=True)
        mem_before = memory_mb()
        try:
            r = await runner()
            r["memory_mb"] = memory_mb()
            r["memory_delta_mb"] = round(r["memory_mb"] - mem_before, 1)
            results.append(r)
            print(f"✅ {r['wall_sec']:.2f}s  (mem: {r['memory_mb']:.0f} MB)")
        except Exception as e:
            print(f"❌ {e}")
            results.append({"status": "error", "wall_sec": 0, "error": str(e), "latencies": {}})
    return results


# ---------------------------------------------------------------------------
# Concurrent load test
# ---------------------------------------------------------------------------

async def run_concurrent_test(runner, concurrent: int) -> dict:
    print(f"\n  Firing {concurrent} concurrent requests...")
    t0 = time.perf_counter()
    tasks = [runner() for _ in range(concurrent)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_wall = time.perf_counter() - t0

    successes = [r for r in results if isinstance(r, dict) and r.get("status") != "error"]
    errors = [r for r in results if not isinstance(r, dict) or r.get("status") == "error"]

    return {
        "concurrent": concurrent,
        "total_wall_sec": round(total_wall, 4),
        "successes": len(successes),
        "errors": len(errors),
        "individual_wall_sec": [r["wall_sec"] for r in successes],
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(seq_results: List[dict], concurrent_result: Optional[dict], args) -> dict:
    # Collect wall times and per-stage latencies
    wall_times = [r["wall_sec"] for r in seq_results if r.get("status") != "error"]
    stage_keys = ["asr_sec", "lid_sec", "translation_sec", "tts_sec", "total_sec"]
    stage_data: Dict[str, List[float]] = {k: [] for k in stage_keys}

    for r in seq_results:
        if r.get("status") == "error":
            continue
        for k in stage_keys:
            v = r.get("latencies", {}).get(k)
            if v is not None:
                stage_data[k].append(v)

    report = {
        "config": {
            "audio_file": args.audio,
            "runs": args.runs,
            "target_language": args.target_language,
            "mode": "remote" if args.url else "local",
        },
        "sequential": {
            "wall_time": compute_stats(wall_times),
            "stages": {k: compute_stats(v) for k, v in stage_data.items() if v},
            "success_rate": f"{len(wall_times)}/{args.runs}",
        },
        "concurrent": concurrent_result,
        "raw_runs": seq_results,
    }
    return report


def print_report(report: dict):
    print("\n" + "=" * 60)
    print("  PERFORMANCE BENCHMARK REPORT")
    print("=" * 60)
    print(f"  Audio: {report['config']['audio_file']}")
    print(f"  Runs: {report['config']['runs']}  |  Mode: {report['config']['mode']}")
    print(f"  Success rate: {report['sequential']['success_rate']}")
    print()
    print("  Wall-time latency (seconds):")
    wt = report["sequential"]["wall_time"]
    print(f"    Min:    {wt.get('min', 'N/A'):.3f}s")
    print(f"    Mean:   {wt.get('mean', 'N/A'):.3f}s")
    print(f"    P50:    {wt.get('p50', 'N/A'):.3f}s")
    print(f"    P95:    {wt.get('p95', 'N/A'):.3f}s")
    print(f"    Max:    {wt.get('max', 'N/A'):.3f}s")
    print(f"    StdDev: {wt.get('stddev', 'N/A'):.3f}s")
    print()
    print("  Per-stage breakdown (mean seconds):")
    for stage, stats in report["sequential"]["stages"].items():
        print(f"    {stage:<25} mean={stats.get('mean', 0):.3f}s  p95={stats.get('p95', 0):.3f}s")

    if report.get("concurrent"):
        c = report["concurrent"]
        print()
        print(f"  Concurrent load ({c['concurrent']} parallel requests):")
        print(f"    Total wall time: {c['total_wall_sec']:.2f}s")
        print(f"    Successes: {c['successes']}  |  Errors: {c['errors']}")
        if c["individual_wall_sec"]:
            print(f"    Individual times: {[f'{x:.2f}s' for x in c['individual_wall_sec']]}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    args = parse_args()

    if not os.path.exists(args.audio):
        print(f"❌ Audio file not found: {args.audio}")
        sys.exit(1)

    ml_models = {}

    if args.url is None:
        # Local mode — load models
        print("Loading AI models (this may take a minute)...")
        sys.path.insert(0, os.path.dirname(__file__))

        from app.services.transcription import TranscriptionService
        from app.services.translation import TranslationService
        from app.services.tts import TTSService

        ml_models["asr"] = TranscriptionService(model_name="base", device="cpu", compute_type="int8")
        ml_models["translation"] = TranslationService()
        ml_models["tts"] = TTSService()
        print("✅ Models loaded\n")

        async def runner():
            return await run_pipeline_local(args.audio, args.target_language, ml_models)
    else:
        async def runner():
            return await run_pipeline_remote(args.audio, args.target_language, args.url)

    # Sequential benchmark
    print(f"Running {args.runs} sequential benchmark runs...")
    seq_results = await run_sequential_benchmark(runner, args.runs)

    # Concurrent test
    concurrent_result = None
    if args.concurrent > 1:
        concurrent_result = await run_concurrent_test(runner, args.concurrent)
        print(f"  → {concurrent_result['successes']}/{args.concurrent} succeeded "
              f"in {concurrent_result['total_wall_sec']:.2f}s total")

    # Build and display report
    report = build_report(seq_results, concurrent_result, args)
    print_report(report)

    # Save JSON report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📄 Full report saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
