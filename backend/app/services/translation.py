"""
TranslationService: Hybrid Multilingual Translation Service.

Priority:
  1. Meta NLLB-200 (facebook/nllb-200-distilled-600M) running locally with int8 dynamic quantization.
     Used whenever available and healthy.
  2. Google Gemini Flash API (e.g. gemini-3.6-flash).
     Used as fallback if NLLB-200 is not loaded, fails, or is disabled.
  3. Echo original text (graceful degraded mode if all providers fail).
"""
import os
import time
import concurrent.futures

from app.core.logger import logger

# ──────────────────────────────────────────────────────────────
# Language Code Mappings
# ──────────────────────────────────────────────────────────────
# ISO 639-1 -> NLLB BCP-47 Language Tag
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

# ISO 639-1 -> Full Language Name for Gemini Prompts
LANG_NAME_MAP: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "ar": "Arabic",
}

MAX_INPUT_TOKENS = 512


class TranslationService:
    """
    Multilingual Translation Service that gives 1st priority to NLLB-200.
    Falls back to Gemini Flash API if NLLB is unavailable or encounters an error.
    """

    def __init__(self):
        from app.config import settings

        self._provider = getattr(settings, "TRANSLATION_PROVIDER", "auto").lower().strip()
        self._nllb_model_name = getattr(settings, "NLLB_MODEL_NAME", "facebook/nllb-200-distilled-600M")

        # NLLB resources
        self.tokenizer = None
        self.model = None
        self._nllb_ready = False

        # Gemini resources
        self._api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self._preferred_gemini = settings.GEMINI_MODEL or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self._candidate_models = [
            self._preferred_gemini,
            "gemini-3.6-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
        ]
        self._candidate_models = list(dict.fromkeys(self._candidate_models))
        self._genai = None
        self._active_gemini_model = self._candidate_models[0]

        # ── 1. Attempt to load NLLB-200 (1st Priority) ────────
        if self._provider in ("auto", "nllb"):
            self._init_nllb()

        # ── 2. Initialize Gemini API (Fallback / Secondary) ───
        if self._provider in ("auto", "gemini"):
            self._init_gemini()

        if not self._nllb_ready and not self._genai:
            logger.warning(
                "Neither local NLLB-200 nor Gemini API could be initialized. "
                "Translation will operate in degraded echo mode."
            )

    def _init_nllb(self):
        """Attempts to load local NLLB-200 tokenizer and quantized model weights."""
        try:
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            logger.info(f"TranslationService: Initializing 1st Priority NLLB-200 ({self._nllb_model_name})...")
            t0 = time.time()
            self.tokenizer = AutoTokenizer.from_pretrained(self._nllb_model_name)
            raw_model = AutoModelForSeq2SeqLM.from_pretrained(
                self._nllb_model_name,
                use_safetensors=False,
            )
            # PyTorch dynamic quantization (Linear -> qint8) for fast CPU inference and lower RAM
            self.model = torch.quantization.quantize_dynamic(
                raw_model,
                {torch.nn.Linear},
                dtype=torch.qint8,
            )
            self.model.eval()
            self._nllb_ready = True
            logger.info(f"TranslationService: NLLB-200 loaded and ready in {time.time() - t0:.2f}s (int8 quantized).")
        except Exception as exc:
            logger.warning(
                f"TranslationService: NLLB-200 could not be loaded ({exc}). "
                "Will rely on Gemini API fallback."
            )
            self.tokenizer = None
            self.model = None
            self._nllb_ready = False

    def _init_gemini(self):
        """Initializes Google Generative AI client."""
        if self._api_key:
            try:
                import google.generativeai as genai  # type: ignore
                genai.configure(api_key=self._api_key)
                self._genai = genai
                logger.info(f"TranslationService: Gemini fallback client ready with preferred model '{self._preferred_gemini}'.")
            except ImportError:
                logger.warning(
                    "google-generativeai package not installed. Gemini fallback unavailable."
                )
        else:
            logger.info("GEMINI_API_KEY not set. Gemini fallback disabled.")

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
        Guarantees 1st priority to NLLB-200, only falling back to Gemini if NLLB fails.
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

        src_name = LANG_NAME_MAP.get(source_lang.lower().strip(), source_lang)
        tgt_name = LANG_NAME_MAP.get(target_lang.lower().strip(), target_lang)

        if source_lang == target_lang:
            return {
                "translated_text": clean_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source_nllb": src_nllb,
                "target_nllb": tgt_nllb,
                "source_name": src_name,
                "target_name": tgt_name,
                "latency_sec": 0.0,
                "method": "no-op",
            }

        t0 = time.time()
        translated = None
        method = "fallback-echo"

        # ── 2. PRIORITY 1: NLLB-200 Local Inference ───────────
        if self._provider in ("auto", "nllb") and self._nllb_ready and self.model is not None and self.tokenizer is not None:
            try:
                import torch
                self.tokenizer.src_lang = src_nllb
                inputs = self.tokenizer(
                    clean_text,
                    return_tensors="pt",
                    max_length=MAX_INPUT_TOKENS,
                    truncation=True,
                )
                forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_nllb)
                with torch.no_grad():
                    generated_tokens = self.model.generate(
                        **inputs,
                        forced_bos_token_id=forced_bos_token_id,
                        max_length=MAX_INPUT_TOKENS,
                        num_beams=2,  # balanced quality & CPU speed
                        early_stopping=True,
                    )
                decoded = self.tokenizer.batch_decode(
                    generated_tokens, skip_special_tokens=True
                )
                if decoded and decoded[0].strip():
                    translated = decoded[0].strip()
                    method = "nllb-200-distilled-600M"
                    logger.info(
                        f"NLLB-200 (Priority 1) succeeded for '{source_lang}'→'{target_lang}' in "
                        f"{time.time() - t0:.2f}s"
                    )
            except Exception as nllb_err:
                logger.warning(
                    f"NLLB-200 translation encountered error: {nllb_err}. "
                    "Engaging fallback provider."
                )
                translated = None

        # ── 3. PRIORITY 2: Gemini Cloud Fallback ──────────────
        if not translated and self._genai and self._provider in ("auto", "gemini"):
            logger.info(f"Attempting Gemini fallback translation for '{source_lang}'→'{target_lang}'...")
            prompt = (
                f"Translate the following text from {src_name} to {tgt_name}. "
                f"Output ONLY the translated text with no explanations, labels, or extra commentary.\n\n"
                f"{clean_text}"
            )

            # Order candidates: try previously working model first, then others
            models_to_try = [self._active_gemini_model] + [
                m for m in self._candidate_models if m != self._active_gemini_model
            ]
            race_models = [m for m in models_to_try if m][:2]

            def _query_model(model_name: str) -> tuple[str, str]:
                client = self._genai.GenerativeModel(model_name)
                resp = client.generate_content(prompt)
                if resp and resp.text:
                    txt = resp.text.strip()
                    if txt:
                        return model_name, txt
                raise ValueError(f"Empty response from {model_name}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(race_models)) as executor:
                futures = {executor.submit(_query_model, m): m for m in race_models}
                for fut in concurrent.futures.as_completed(futures):
                    m_name = futures[fut]
                    try:
                        winning_model, res_text = fut.result()
                        translated = res_text
                        method = f"gemini:{winning_model}"
                        self._active_gemini_model = winning_model
                        logger.info(
                            f"Gemini fallback won by '{winning_model}' for '{source_lang}'→'{target_lang}' in "
                            f"{time.time() - t0:.2f}s"
                        )
                        for remaining_fut in futures:
                            remaining_fut.cancel()
                        break
                    except Exception as m_err:
                        logger.warning(f"Gemini candidate '{m_name}' failed: {m_err}")

        # ── 4. PRIORITY 3: Fallback Echo ──────────────────────
        if not translated:
            logger.warning("All translation providers failed. Falling back to echo.")
            translated = clean_text
            method = "fallback-echo"

        latency = round(time.time() - t0, 3)

        return {
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "source_nllb": src_nllb,
            "target_nllb": tgt_nllb,
            "source_name": src_name,
            "target_name": tgt_name,
            "latency_sec": latency,
            "method": method,
        }

