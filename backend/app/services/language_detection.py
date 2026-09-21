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
    def detect_language(text: str, whisper_lang: str = None, whisper_prob: float = 0.0) -> dict:
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
        
        # 2. Check if Whisper has a high-confidence result
        if whisper_lang and whisper_lang != "unknown" and whisper_prob >= 0.6:
            logger.info(f"Using Whisper primary language detection: '{whisper_lang}' (confidence: {whisper_prob:.4f})")
            return {
                "detected_language": whisper_lang.lower(),
                "confidence": round(whisper_prob, 4),
                "source": "whisper"
            }

        # 3. Fallback: Run text-based language detection on the transcribed text
        if clean_text:
            try:
                # detect_langs returns a list of Language objects sorted by probability descending
                predictions = detect_langs(clean_text)
                if predictions:
                    best_match = predictions[0]
                    detected_lang = best_match.lang.lower()
                    confidence = best_match.prob
                    
                    logger.info(
                        f"Low Whisper confidence ({whisper_prob:.4f}). "
                        f"Text-based fallback (langdetect) resolved: '{detected_lang}' (confidence: {confidence:.4f})"
                    )
                    return {
                        "detected_language": detected_lang,
                        "confidence": round(confidence, 4),
                        "source": "langdetect"
                    }
            except LangDetectException as e:
                logger.warning(f"Text-based language detection failed (empty or un-featureful text): {e}")
            except Exception as e:
                logger.error(f"Unexpected error in langdetect: {e}", exc_info=True)

        # 4. Final Fallback: Use low-confidence Whisper language if available, otherwise default to "en"
        if whisper_lang and whisper_lang != "unknown":
            logger.warning(
                f"LID Fallback: both primary and text detection failed/low confidence. "
                f"Falling back to low-confidence Whisper: '{whisper_lang}' (confidence: {whisper_prob:.4f})"
            )
            return {
                "detected_language": whisper_lang.lower(),
                "confidence": round(whisper_prob, 4),
                "source": "fallback"
            }

        logger.warning("LID Fallback: No transcription text or audio detection available. Defaulting to 'en'.")
        return {
            "detected_language": "en",
            "confidence": 1.0,
            "source": "fallback"
        }
