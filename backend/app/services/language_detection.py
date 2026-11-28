import os
from app.core.logger import logger
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

# Force deterministic results from langdetect
DetectorFactory.seed = 0

# Define supported source languages for this project (NLLB / MarianMT compatible standard codes)
SUPPORTED_LANGUAGES = {"en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ru", "hi", "ar"}

class LanguageDetectionService:
    @staticmethod
    def is_language_supported(lang_code: str) -> bool:
        """
        Check if the given ISO 639-1 language code is supported by the system.
        """
        if not lang_code:
            return False
        return lang_code.lower() in SUPPORTED_LANGUAGES

    @staticmethod
    def detect_language(text: str, whisper_lang: str | None = None, whisper_prob: float = 0.0) -> dict:
        """
        Detects the language of the audio/text.
        Uses Whisper's audio-based detection as primary source if confidence is high.
        Falls back to text-based detection using langdetect if Whisper confidence is low.
        
        Args:
            text (str): The transcribed text.
            whisper_lang (str): The language code detected by Whisper (optional).
            whisper_prob (float): The language probability returned by Whisper (optional).
            
        Returns:
            dict: {
                "detected_language": str, (standard 2-character code)
                "confidence": float,
                "source": str ("whisper", "langdetect", or "fallback")
            }
        """
        # 1. Clean input text
        clean_text = text.strip() if text else ""
        
        # 2. If Whisper detected a language:
        # Check if it is directly supported
        if whisper_lang and whisper_lang != "unknown":
            wl = whisper_lang.lower().strip()
            # If whisper says a supported language with decent confidence, use it
            if wl in SUPPORTED_LANGUAGES and whisper_prob >= 0.5:
                logger.info(f"Using Whisper primary language detection: '{wl}' (confidence: {whisper_prob:.4f})")
                return {
                    "detected_language": wl,
                    "confidence": round(whisper_prob, 4),
                    "source": "whisper"
                }

        # 3. Fallback: Run text-based language detection on the transcribed text
        if clean_text:
            try:
                # detect_langs returns a list of Language objects sorted by probability descending
                predictions = detect_langs(clean_text)
                if predictions:
                    # Look for the highest confidence supported language first
                    for pred in predictions:
                        pl = pred.lang.lower().strip()
                        if pl in SUPPORTED_LANGUAGES and pred.prob >= 0.4:
                            logger.info(
                                f"Text-based language detection (langdetect) resolved supported language: '{pl}' (confidence: {pred.prob:.4f})"
                            )
                            return {
                                "detected_language": pl,
                                "confidence": round(pred.prob, 4),
                                "source": "langdetect"
                            }
                    
                    # If none matched supported, take the best match
                    best_match = predictions[0]
                    detected_lang = best_match.lang.lower().strip()
                    logger.info(
                        f"Text-based fallback (langdetect) resolved: '{detected_lang}' (confidence: {best_match.prob:.4f})"
                    )
                    return {
                        "detected_language": detected_lang,
                        "confidence": round(best_match.prob, 4),
                        "source": "langdetect"
                    }
            except LangDetectException as e:
                logger.warning(f"Text-based language detection failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in langdetect: {e}", exc_info=True)

        # 4. If whisper language was supported, use it even with lower confidence
        if whisper_lang and whisper_lang != "unknown":
            wl = whisper_lang.lower().strip()
            if wl in SUPPORTED_LANGUAGES:
                return {
                    "detected_language": wl,
                    "confidence": round(whisper_prob, 4),
                    "source": "whisper"
                }

        # 5. Default fallback to English ('en')
        return {
            "detected_language": "en",
            "confidence": 0.8,
            "source": "fallback"
        }
