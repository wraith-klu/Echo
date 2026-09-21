"""
TranslationService: Gemini Flash API-based multilingual translation service.

Uses Google Gemini 1.5 Flash (free-tier friendly) for many-to-many translation
instead of the local 2GB NLLB-200 model, enabling deployment on Render's free tier
with only 512 MB RAM.

Falls back gracefully if GEMINI_API_KEY is not set.
"""
import os
import time

from app.core.logger import logger

# ──────────────────────────────────────────────────────────────
# ISO 639-1 → full language name for Gemini prompt
# ──────────────────────────────────────────────────────────────
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

# Keep NLLB_LANG_MAP as an alias so pipeline.py import doesn't break
NLLB_LANG_MAP = LANG_NAME_MAP


class TranslationService:
    """
    Wraps Google Gemini Flash API for lightweight cloud-based translation.
    No local model weights — ideal for free-tier hosting with limited RAM.
    """

    def __init__(self):
        from app.config import settings
        self._api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self._model_name = settings.GEMINI_MODEL or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self._candidate_models = [
            self._model_name,
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
        ]
        # De-duplicate while preserving order
        self._candidate_models = list(dict.fromkeys(self._candidate_models))
        self._genai = None
        self._active_model_name = None

        if self._api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._genai = genai
                self._active_model_name = self._candidate_models[0]
                logger.info(f"TranslationService: Gemini client initialized with preferred model '{self._active_model_name}'.")
            except ImportError:
                logger.warning(
                    "google-generativeai package not installed. "
                    "Translation will echo input text. Install with: pip install google-generativeai"
                )
        else:
            logger.warning(
                "GEMINI_API_KEY not set. Translation will echo input text. "
                "Set GEMINI_API_KEY in environment to enable real translation."
            )

    # ──────────────────────────────────────────────────────────
    # Public API (same interface as old NLLB TranslationService)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_nllb_code(iso_code: str) -> str | None:
        """Return the language name for an ISO 639-1 code, or None if unsupported."""
        return LANG_NAME_MAP.get(iso_code.lower().strip())

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict:
        """
        Translate `text` from `source_lang` to `target_lang` via Gemini Flash API.

        Args:
            text:        The transcribed source text.
            source_lang: ISO 639-1 code (e.g. "en", "es").
            target_lang: ISO 639-1 code for the desired output language.

        Returns:
            {
              "translated_text": str,
              "source_lang":     str,
              "target_lang":     str,
              "source_name":     str,
              "target_name":     str,
              "latency_sec":     float,
              "method":          str,
            }

        Raises:
            ValueError for unsupported languages or empty text.
        """
        # ── 1. Validate inputs ────────────────────────────────
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("Translation input text is empty.")

        src_name = LANG_NAME_MAP.get(source_lang.lower().strip())
        tgt_name = LANG_NAME_MAP.get(target_lang.lower().strip())

        if src_name is None:
            raise ValueError(
                f"Unsupported source language '{source_lang}'. "
                f"Supported: {sorted(LANG_NAME_MAP.keys())}"
            )
        if tgt_name is None:
            raise ValueError(
                f"Unsupported target language '{target_lang}'. "
                f"Supported: {sorted(LANG_NAME_MAP.keys())}"
            )

        if source_lang == target_lang:
            return {
                "translated_text": clean_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source_name": src_name,
                "target_name": tgt_name,
                "latency_sec": 0.0,
                "method": "no-op",
            }

        t0 = time.time()

        # ── 2. Attempt Gemini API translation with model fallbacks ───
        if self._genai:
            prompt = (
                f"Translate the following text from {src_name} to {tgt_name}. "
                f"Output ONLY the translated text with no explanations, labels, or extra commentary.\n\n"
                f"{clean_text}"
            )

            # Order candidates: try previously working model first, then others
            models_to_try = [self._active_model_name] + [
                m for m in self._candidate_models if m != self._active_model_name
            ]

            translated = None
            method = "fallback-echo"

            for model_name in models_to_try:
                try:
                    client = self._genai.GenerativeModel(model_name)
                    response = client.generate_content(prompt)
                    if response and response.text:
                        translated = response.text.strip()
                        method = f"gemini:{model_name}"
                        self._active_model_name = model_name
                        logger.info(
                            f"Gemini translation '{source_lang}'→'{target_lang}' succeeded using '{model_name}' in "
                            f"{time.time()-t0:.2f}s"
                        )
                        break
                except Exception as api_err:
                    logger.warning(
                        f"Gemini model '{model_name}' translation failed: {api_err}. Trying next candidate..."
                    )

            if not translated:
                logger.warning("All Gemini candidate models failed. Falling back to echo.")
                translated = clean_text
                method = "fallback-echo"
        else:
            # No API key — echo source text as placeholder
            translated = clean_text
            method = "fallback-echo"

        latency = round(time.time() - t0, 3)

        return {
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "source_name": src_name,
            "target_name": tgt_name,
            "latency_sec": latency,
            "method": method,
        }
