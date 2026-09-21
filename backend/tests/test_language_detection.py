"""
test_language_detection.py — Unit tests for LanguageDetectionService (Step 4).

Tests:
  - is_language_supported for known and unknown codes
  - detect_language using Whisper override (high confidence)
  - detect_language falling back to langdetect
  - detect_language fallback when text is too short
"""

import pytest
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES


class TestIsLanguageSupported:

    @pytest.mark.parametrize("lang", list(SUPPORTED_LANGUAGES))
    def test_supported_languages_return_true(self, lang):
        assert LanguageDetectionService.is_language_supported(lang) is True

    @pytest.mark.parametrize("lang", ["xx", "zz", "tlh", "", "123"])
    def test_unsupported_languages_return_false(self, lang):
        assert LanguageDetectionService.is_language_supported(lang) is False

    def test_case_insensitive(self):
        assert LanguageDetectionService.is_language_supported("EN") is True
        assert LanguageDetectionService.is_language_supported("Es") is True


class TestDetectLanguage:

    def test_whisper_high_confidence_used(self):
        result = LanguageDetectionService.detect_language(
            text="Hello, how are you?",
            whisper_lang="en",
            whisper_prob=0.95
        )
        assert result["detected_language"] == "en"
        assert result["source"] == "whisper"

    def test_whisper_low_confidence_falls_back(self):
        # Whisper probability below threshold → should use langdetect or fallback
        result = LanguageDetectionService.detect_language(
            text="Hello, how are you?",
            whisper_lang="fr",
            whisper_prob=0.20
        )
        # langdetect should detect English
        assert result["detected_language"] in SUPPORTED_LANGUAGES

    def test_no_whisper_uses_langdetect(self):
        result = LanguageDetectionService.detect_language(
            text="Hello, how are you?",
        )
        assert "detected_language" in result
        assert "confidence" in result
        assert "source" in result

    def test_empty_text_returns_fallback(self):
        result = LanguageDetectionService.detect_language(text="")
        assert result["detected_language"] in SUPPORTED_LANGUAGES or result["detected_language"] == "en"

    def test_result_schema(self):
        result = LanguageDetectionService.detect_language(
            text="Bonjour le monde",
            whisper_lang="fr",
            whisper_prob=0.98
        )
        assert set(result.keys()) >= {"detected_language", "confidence", "source"}
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
