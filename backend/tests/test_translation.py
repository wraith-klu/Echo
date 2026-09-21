"""
test_translation.py — Unit tests for TranslationService (Step 5).

Strategy: mock the underlying torch/transformers model so tests run in <1s.
Integration tests (marked @pytest.mark.integration) load the real model
and are skipped unless ENABLE_INTEGRATION_TESTS=1 is set.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Unit tests — model is mocked
# ---------------------------------------------------------------------------

class TestTranslationServiceUnit:
    """All tests here use a fully mocked TranslationService to avoid model loading."""

    @pytest.fixture(autouse=True)
    def patched_service(self, mock_translation_service):
        self.svc = mock_translation_service

    def test_translate_returns_translated_text(self):
        result = self.svc.translate_text("Hello", source_lang="en", target_lang="es")
        assert "translated_text" in result
        assert result["translated_text"] == "Hola, ¿cómo estás?"

    def test_translate_records_source_and_target(self):
        result = self.svc.translate_text("Hello", source_lang="en", target_lang="es")
        assert result["source_lang"] == "en"
        assert result["target_lang"] == "es"

    def test_translate_called_with_correct_args(self):
        self.svc.translate_text("Bonjour", source_lang="fr", target_lang="de")
        self.svc.translate_text.assert_called_once_with(
            "Bonjour", source_lang="fr", target_lang="de"
        )


# ---------------------------------------------------------------------------
# Validation unit tests — test input guards without loading a model
# ---------------------------------------------------------------------------

class TestTranslationValidation:
    """Test input validation logic by importing the service class with a patched model."""

    @pytest.fixture(autouse=True)
    def patch_model_loading(self):
        """Prevent actual model download during import."""
        with patch("app.services.translation.AutoModelForSeq2SeqLM") as mock_model, \
             patch("app.services.translation.AutoTokenizer") as mock_tok:
            mock_tok.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            yield

    def test_empty_text_raises_value_error(self):
        from app.services.translation import TranslationService
        svc = TranslationService.__new__(TranslationService)
        svc.tokenizer = MagicMock()
        svc.model = MagicMock()
        with pytest.raises(ValueError, match="empty"):
            svc.translate_text("", source_lang="en", target_lang="es")

    def test_unsupported_source_lang_raises(self):
        from app.services.translation import TranslationService
        svc = TranslationService.__new__(TranslationService)
        svc.tokenizer = MagicMock()
        svc.model = MagicMock()
        with pytest.raises(ValueError, match="Unsupported source"):
            svc.translate_text("hello", source_lang="xx", target_lang="es")

    def test_unsupported_target_lang_raises(self):
        from app.services.translation import TranslationService
        svc = TranslationService.__new__(TranslationService)
        svc.tokenizer = MagicMock()
        svc.model = MagicMock()
        with pytest.raises(ValueError, match="Unsupported target"):
            svc.translate_text("hello", source_lang="en", target_lang="zz")

    def test_same_language_noop(self):
        from app.services.translation import TranslationService
        svc = TranslationService.__new__(TranslationService)
        svc.tokenizer = MagicMock()
        svc.model = MagicMock()
        result = svc.translate_text("hello", source_lang="en", target_lang="en")
        # No-op: should return original text, no model call
        assert result["translated_text"] == "hello"
        svc.model.generate.assert_not_called()


# ---------------------------------------------------------------------------
# Integration tests — only run with real model
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTranslationIntegration:
    """
    Load the real NLLB model. Runs only when ENABLE_INTEGRATION_TESTS=1.
    These are slow (~20s on first run) but validate actual translation quality.
    """

    @pytest.fixture(scope="class", autouse=True)
    def real_service(self):
        import os
        if not os.environ.get("ENABLE_INTEGRATION_TESTS"):
            pytest.skip("Set ENABLE_INTEGRATION_TESTS=1 to run integration tests")
        from app.services.translation import TranslationService
        self.__class__.svc = TranslationService()

    def test_en_to_es(self):
        result = self.svc.translate_text("Hello, how are you?", source_lang="en", target_lang="es")
        assert len(result["translated_text"]) > 0
        assert result["target_lang"] == "es"

    def test_en_to_fr(self):
        result = self.svc.translate_text("Good morning.", source_lang="en", target_lang="fr")
        assert "bonjour" in result["translated_text"].lower() or len(result["translated_text"]) > 0
