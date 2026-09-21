#!/usr/bin/env python3
"""
eval_accuracy.py — Transcription accuracy (WER) and translation quality evaluation.

Metrics:
  - Word Error Rate (WER): measures ASR accuracy against known ground-truth transcripts.
    WER = (S + D + I) / N
    where S=substitutions, D=deletions, I=insertions, N=total reference words

  - BLEU score: measures translation quality against human reference translations.
    Implemented using sacrebleu (pip install sacrebleu).

Usage:
  # WER evaluation on a set of audio files with ground-truth transcripts:
  poetry run python eval_accuracy.py wer \
      --audio test_data/en_hello.wav --ref "hello how are you" \
      --audio test_data/en_weather.wav --ref "the weather is nice today"

  # BLEU evaluation on translation pairs:
  poetry run python eval_accuracy.py bleu \
      --hypothesis "Hola, cómo estás" --reference "Hola, ¿cómo estás?" \
      --hypothesis "El tiempo es bueno" --reference "El tiempo es agradable hoy"

  # Full evaluation on a CSV file:
  poetry run python eval_accuracy.py csv --file eval_data.csv
  # CSV format: audio_path,reference_transcript,reference_translation,target_lang
"""

import argparse
import sys
import os
import re
import json
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# WER implementation (no external library needed)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse spaces."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def compute_wer(reference: str, hypothesis: str) -> dict:
    """
    Compute Word Error Rate using dynamic programming (Wagner-Fischer algorithm).

    Returns:
        dict with keys: wer, substitutions, deletions, insertions,
                         ref_words, hyp_words
    """
    ref = _normalize(reference).split()
    hyp = _normalize(hypothesis).split()

    N = len(ref)
    M = len(hyp)

    # Build edit distance matrix
    dp = [[0] * (M + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        dp[i][0] = i
    for j in range(M + 1):
        dp[0][j] = j

    for i in range(1, N + 1):
        for j in range(1, M + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1]   # substitution
                )

    edit_distance = dp[N][M]
    wer = edit_distance / max(N, 1)

    return {
        "wer": round(wer, 4),
        "wer_pct": round(wer * 100, 2),
        "edit_distance": edit_distance,
        "ref_words": N,
        "hyp_words": M,
        "reference": reference,
        "hypothesis": hypothesis,
    }


# ---------------------------------------------------------------------------
# BLEU score (using sacrebleu if available)
# ---------------------------------------------------------------------------

def compute_bleu(hypotheses: List[str], references: List[str]) -> dict:
    """
    Compute corpus-level BLEU score.
    Falls back to a simple unigram precision if sacrebleu not installed.
    """
    try:
        import importlib
        sacrebleu = importlib.import_module("sacrebleu")
        bleu = sacrebleu.corpus_bleu(hypotheses, [references])
        return {
            "bleu": round(bleu.score, 2),
            "method": "sacrebleu",
            "hypotheses": len(hypotheses),
            "brevity_penalty": round(bleu.bp, 4),
        }
    except (ImportError, ModuleNotFoundError):
        # Fallback: unigram precision
        total_match = 0
        total_hyp = 0
        for hyp, ref in zip(hypotheses, references):
            h_words = _normalize(hyp).split()
            r_words = set(_normalize(ref).split())
            total_match += sum(1 for w in h_words if w in r_words)
            total_hyp += len(h_words)
        precision = total_match / max(total_hyp, 1)
        return {
            "bleu": round(precision * 100, 2),
            "method": "unigram_precision_fallback (install sacrebleu for real BLEU)",
            "hypotheses": len(hypotheses),
        }


# ---------------------------------------------------------------------------
# Transcription runner
# ---------------------------------------------------------------------------

def transcribe_file(audio_path: str) -> str:
    """Run Whisper ASR on a file and return the transcribed text."""
    from app.services.transcription import TranscriptionService
    svc = TranscriptionService(model_name="base", device="cpu", compute_type="int8")
    result = svc.transcribe_audio(audio_path)
    return result.get("text", "").strip()


# ---------------------------------------------------------------------------
# WER evaluation mode
# ---------------------------------------------------------------------------

def run_wer_eval(audio_ref_pairs: List[Tuple[str, str]]) -> None:
    print("\n" + "=" * 60)
    print("  TRANSCRIPTION ACCURACY — Word Error Rate (WER)")
    print("=" * 60)

    all_wers = []
    results = []

    print("\nLoading Whisper ASR model...")
    from app.services.transcription import TranscriptionService
    svc = TranscriptionService(model_name="base", device="cpu", compute_type="int8")
    print("✅ Model loaded\n")

    for audio_path, reference in audio_ref_pairs:
        print(f"  File: {audio_path}")
        hyp = svc.transcribe_audio(audio_path).get("text", "").strip()
        wer_info = compute_wer(reference, hyp)
        all_wers.append(wer_info["wer"])
        results.append(wer_info)

        print(f"    Ref:  {reference}")
        print(f"    Hyp:  {hyp}")
        print(f"    WER:  {wer_info['wer_pct']:.1f}%  ({wer_info['edit_distance']} edits / {wer_info['ref_words']} words)")
        print()

    # Summary
    mean_wer = sum(all_wers) / len(all_wers) if all_wers else 0
    print(f"  Mean WER across {len(all_wers)} files: {mean_wer * 100:.1f}%")
    print()
    print("  Interpretation:")
    print("    < 5%  : Excellent (production ASR quality)")
    print("    5-15% : Good (research/capstone demo quality)")
    print("    15-30%: Acceptable for noisy environments")
    print("    > 30% : Needs improvement")

    print("\n" + "=" * 60)
    return results


# ---------------------------------------------------------------------------
# BLEU evaluation mode
# ---------------------------------------------------------------------------

def run_bleu_eval(hyp_ref_pairs: List[Tuple[str, str]]) -> None:
    print("\n" + "=" * 60)
    print("  TRANSLATION QUALITY — BLEU Score")
    print("=" * 60)

    hypotheses = [h for h, r in hyp_ref_pairs]
    references = [r for h, r in hyp_ref_pairs]

    for i, (hyp, ref) in enumerate(hyp_ref_pairs, 1):
        print(f"\n  Pair {i}:")
        print(f"    Hypothesis: {hyp}")
        print(f"    Reference:  {ref}")

    bleu = compute_bleu(hypotheses, references)
    print(f"\n  Corpus BLEU score: {bleu['bleu']:.1f}  (method: {bleu['method']})")
    print()
    print("  Interpretation:")
    print("    > 40  : High quality translation")
    print("    25-40 : Good translation")
    print("    15-25 : Understandable translation")
    print("    < 15  : Poor quality")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CSV mode
# ---------------------------------------------------------------------------

def run_csv_eval(csv_path: str) -> None:
    import csv
    audio_ref_pairs = []
    hyp_ref_pairs = []

    from app.services.transcription import TranscriptionService
    from app.services.translation import TranslationService

    asr = TranscriptionService(model_name="base", device="cpu", compute_type="int8")
    mt = TranslationService()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio = row.get("audio_path", "").strip()
            ref_transcript = row.get("reference_transcript", "").strip()
            ref_translation = row.get("reference_translation", "").strip()
            target_lang = row.get("target_lang", "es").strip()

            if audio and ref_transcript:
                hyp = asr.transcribe_audio(audio).get("text", "").strip()
                audio_ref_pairs.append((audio, ref_transcript))

                wer = compute_wer(ref_transcript, hyp)
                print(f"  {audio}: WER={wer['wer_pct']:.1f}%")

                if ref_translation:
                    try:
                        trans = mt.translate_text(hyp, source_lang="en", target_lang=target_lang)
                        hyp_ref_pairs.append((trans["translated_text"], ref_translation))
                    except Exception as e:
                        print(f"    Translation failed: {e}")

    if hyp_ref_pairs:
        bleu = compute_bleu(
            [h for h, r in hyp_ref_pairs],
            [r for h, r in hyp_ref_pairs]
        )
        print(f"\n  Corpus BLEU: {bleu['bleu']:.1f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode")

    # WER mode
    wer_p = subparsers.add_parser("wer", help="Compute WER on audio files")
    wer_p.add_argument("--audio", action="append", dest="audios", required=True)
    wer_p.add_argument("--ref", action="append", dest="refs", required=True)

    # BLEU mode
    bleu_p = subparsers.add_parser("bleu", help="Compute BLEU on translation pairs")
    bleu_p.add_argument("--hypothesis", action="append", dest="hyps", required=True)
    bleu_p.add_argument("--reference", action="append", dest="refs", required=True)

    # CSV mode
    csv_p = subparsers.add_parser("csv", help="Run full eval from a CSV file")
    csv_p.add_argument("--file", required=True)

    args = parser.parse_args()

    if args.mode == "wer":
        pairs = list(zip(args.audios, args.refs))
        run_wer_eval(pairs)
    elif args.mode == "bleu":
        pairs = list(zip(args.hyps, args.refs))
        run_bleu_eval(pairs)
    elif args.mode == "csv":
        run_csv_eval(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
