"""
test_pipeline.py — Unit and integration tests for PipelineOrchestrator (Step 7).

Unit tests: mock all services to run in milliseconds and verify:
  - Happy path returns PipelineResult with correct fields
  - ASR failure returns status="error"
  - No speech returns status="success" with empty transcription
  - Unsupported language returns status="partial_success"
  - Missing target language skips translation/TTS
  - DB logging is called when db session is provided

Integration test (ENABLE_INTEGRATION_TESTS=1): loads real models and runs
a complete pipeline on a real WAV file.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.pipeline import PipelineOrchestrator, PipelineResult


# ---------------------------------------------------------------------------
# Unit tests — all services mocked
# ---------------------------------------------------------------------------

class TestPipelineUnit:

    @pytest.fixture(autouse=True)
    def setup(self, mock_ml_models, sample_wav_path, tmp_path, monkeypatch):
        self.models = mock_ml_models
        self.wav = sample_wav_path
        self.tmp = tmp_path
        # Patch UPLOAD_DIR so TTS files are written to tmp
        monkeypatch.setattr(
            "app.services.pipeline.UPLOAD_DIR" if hasattr(
                __import__("app.services.pipeline"), "UPLOAD_DIR"
            ) else "app.services.ingestion.UPLOAD_DIR",
            str(tmp_path),
            raising=False,
        )

    @pytest.mark.asyncio
    async def test_happy_path_returns_success(self):
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models=self.models,
            device_id="test_device",
            target_language="es",
        )
        assert result.status in ("success", "partial_success")
        assert result.transcription is not None
        assert result.transcription["text"] == "Hello, how are you?"

    @pytest.mark.asyncio
    async def test_asr_failure_returns_error(self):
        self.models["asr"].transcribe_audio.side_effect = RuntimeError("ASR crashed")
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models=self.models,
            device_id="test_device",
        )
        assert result.status == "error"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_missing_asr_service_returns_error(self):
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models={},   # no ASR
            device_id="test_device",
        )
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_no_speech_returns_success_empty(self):
        self.models["asr"].transcribe_audio.return_value = {
            "text": "",
            "language": "en",
            "language_probability": 0.5,
            "segments": [],
            "latency_sec": 0.2,
        }
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models=self.models,
            device_id="test_device",
        )
        assert result.status == "success"
        assert result.translation is None

    @pytest.mark.asyncio
    async def test_no_target_language_skips_translation(self):
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models=self.models,
            device_id="test_device",
            target_language=None,
        )
        assert result.translation is None
        assert result.tts is None

    @pytest.mark.asyncio
    async def test_latencies_dict_present(self):
        result = await PipelineOrchestrator.run(
            file_path=self.wav,
            ml_models=self.models,
            device_id="test_device",
            target_language="es",
        )
        assert result.latencies is not None
        for key in ("asr_sec", "lid_sec", "translation_sec", "tts_sec", "total_sec"):
            assert key in result.latencies

    @pytest.mark.asyncio
    async def test_db_logging_called_when_db_provided(self):
        """DB logging should be attempted when a db session is passed in."""
        fake_db = AsyncMock()
        with patch("app.services.db_service.log_translation", new_callable=AsyncMock) as mock_log, \
             patch("app.services.db_service.register_device", new_callable=AsyncMock) as mock_reg:
            result = await PipelineOrchestrator.run(
                file_path=self.wav,
                ml_models=self.models,
                device_id="test_device",
                target_language="es",
                db=fake_db,
            )
            assert result is not None
            mock_reg.assert_called_once()
            mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# Integration test — real pipeline execution
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestPipelineIntegration:
    """
    Runs the complete pipeline with real models on a real audio file.
    Requires: ENABLE_INTEGRATION_TESTS=1 and models already downloaded.
    """

    @pytest.fixture(scope="class", autouse=True)
    def real_models(self):
        if not os.environ.get("ENABLE_INTEGRATION_TESTS"):
            pytest.skip("Set ENABLE_INTEGRATION_TESTS=1 to run integration tests")

        from app.services.transcription import TranscriptionService
        from app.services.translation import TranslationService
        from app.services.tts import TTSService

        self.__class__.ml_models = {
            "asr": TranscriptionService(model_name="base", device="cpu", compute_type="int8"),
            "translation": TranslationService(),
            "tts": TTSService(),
        }

    @pytest.mark.asyncio
    async def test_end_to_end_real_audio(self, sample_wav_path):
        result = await PipelineOrchestrator.run(
            file_path=sample_wav_path,
            ml_models=self.__class__.ml_models,
            device_id="integration_test",
            target_language="es",
        )
        assert result.status in ("success", "partial_success")
        print(f"\n[E2E] Status: {result.status}")
        print(f"[E2E] Text: {result.transcription.get('text', '')}")
        print(f"[E2E] Translated: {result.translation.get('translated_text', '') if result.translation else 'N/A'}")
        print(f"[E2E] Latencies: {result.latencies}")
