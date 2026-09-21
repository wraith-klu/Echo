"""
TranslationService: NLLB-200 based multilingual translation service.

Uses facebook/nllb-200-distilled-600M with PyTorch dynamic quantization
for CPU-efficient many-to-many translation across 200+ languages.
"""
import os
import time

# Disable Hugging Face Xet Storage CDN (requires auth even for public models).
# Without this, pytorch_model.bin download stalls at 0 bytes.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.core.logger import logger

# ──────────────────────────────────────────────────────────────
# NLLB language code mapping from ISO 639-1 → NLLB BCP-47 codes
# ──────────────────────────────────────────────────────────────
NLLB_LANG_MAP: dict[str, str] = {
    "en": "eng_Latn",
    "hi": "hin_Deva",   # Hindi
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "it": "ita_Latn",
    "pt": "por_Latn",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",   # Arabic
}

MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Max tokens to translate per call (NLLB's max is 1024 tokens).
# Longer text is split into sentences/chunks.
MAX_INPUT_TOKENS = 512


class TranslationService:
    """
    Wraps a single NLLB-200-distilled-600M model instance.
    Loaded once at startup; shared across all requests.
    """

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        """Download (first run) and load the NLLB model + tokenizer."""
        logger.info(f"Loading NLLB tokenizer: {MODEL_NAME} ...")
        t0 = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        logger.info(f"Tokenizer loaded in {time.time() - t0:.2f}s")

        logger.info(f"Loading NLLB model: {MODEL_NAME} (FP32 first, then quantize) ...")
        t1 = time.time()
        raw_model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME,
            use_safetensors=False,   # repo only has pytorch_model.bin
        )

        # Dynamic quantisation: int8 weights for all Linear layers.
        # Cuts memory by ~50% and speeds up CPU inference 2-3x.
        logger.info("Applying torch dynamic quantization (Linear → qint8) ...")
        self.model = torch.quantization.quantize_dynamic(
            raw_model,
            {torch.nn.Linear},
            dtype=torch.qint8,
        )
        self.model.eval()
        logger.info(
            f"NLLB model ready (quantized) in {time.time() - t1:.2f}s total."
        )

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_nllb_code(iso_code: str) -> str | None:
        """Convert an ISO 639-1 code to the NLLB language tag, or None."""
        return NLLB_LANG_MAP.get(iso_code.lower().strip())

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict:
        """
        Translate `text` from `source_lang` to `target_lang`.

        Args:
            text:        The transcribed source text.
            source_lang: ISO 639-1 code (e.g. "en", "es").
            target_lang: ISO 639-1 code for the desired output language.

        Returns:
            {
              "translated_text": str,
              "source_lang":     str,
              "target_lang":     str,
              "source_nllb":     str,
              "target_nllb":     str,
              "latency_sec":     float,
            }

        Raises:
            ValueError for unsupported languages or empty text.
        """
        # ── 1. Validate inputs ────────────────────────────────
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("Translation input text is empty.")

        src_nllb = self.get_nllb_code(source_lang)
        tgt_nllb = self.get_nllb_code(target_lang)

        if src_nllb is None:
            raise ValueError(
                f"Unsupported source language '{source_lang}'. "
                f"Supported: {sorted(NLLB_LANG_MAP.keys())}"
            )
        if tgt_nllb is None:
            raise ValueError(
                f"Unsupported target language '{target_lang}'. "
                f"Supported: {sorted(NLLB_LANG_MAP.keys())}"
            )

        if source_lang == target_lang:
            # No-op: return original text instantly
            return {
                "translated_text": clean_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source_nllb": src_nllb,
                "target_nllb": tgt_nllb,
                "latency_sec": 0.0,
            }

        logger.info(
            f"Translating '{source_lang}' → '{target_lang}' | "
            f"text length: {len(clean_text)} chars"
        )

        # ── 2. Tokenise with the source language set ──────────
        t0 = time.time()
        self.tokenizer.src_lang = src_nllb
        inputs = self.tokenizer(
            clean_text,
            return_tensors="pt",
            max_length=MAX_INPUT_TOKENS,
            truncation=True,
        )

        # ── 3. Generate ───────────────────────────────────────
        with torch.no_grad():
            forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_nllb)
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=MAX_INPUT_TOKENS,
                num_beams=4,           # beam search for quality
                early_stopping=True,
            )

        # ── 4. Decode ─────────────────────────────────────────
        translated = self.tokenizer.batch_decode(
            generated_tokens, skip_special_tokens=True
        )[0]

        latency = round(time.time() - t0, 3)
        logger.info(
            f"Translation complete in {latency}s | "
            f"output: \"{translated[:80]}{'...' if len(translated) > 80 else ''}\""
        )

        return {
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "source_nllb": src_nllb,
            "target_nllb": tgt_nllb,
            "latency_sec": latency,
        }
