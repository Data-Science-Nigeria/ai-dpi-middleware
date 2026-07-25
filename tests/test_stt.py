"""Tests for the Speech-to-Text endpoint – all providers, validation, caching."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

STT_URL = "/api/v1/stt/transcribe"

_MOCK_RESULT = {"text": "Hello world", "language": "en", "duration": 1.5}


def _stt_form(
    file_bytes: bytes,
    filename: str = "audio.wav",
    provider: str = "groq",
    model: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
    special_words: str | None = None,
    timestamp: str = "none",
) -> dict:
    data: dict = {"provider": provider, "timestamp": timestamp}
    if model:
        data["model"] = model
    if language:
        data["language"] = language
    if prompt:
        data["prompt"] = prompt
    if special_words:
        data["special_words"] = special_words
    return data


# ── Provider routing – happy path ─────────────────────────────────────────────

class TestSTTProviderRouting:

    @pytest.mark.parametrize("provider,model,extra", [
        ("groq", "whisper-large-v3-turbo", {}),
        ("openai", "gpt-4o-mini-transcribe", {}),
        ("deepgram", "nova-3", {}),
        ("spitch", "legacy", {"language": "en"}),
        ("intron", "sahara-v1", {"language": "en"}),
    ])
    async def test_provider_routes_correctly(
        self,
        user_client: AsyncClient,
        tiny_wav: bytes,
        provider: str,
        model: str,
        extra: dict,
    ):
        mock_path = f"app.services.stt.providers.{provider}.transcribe"
        with patch(mock_path, new_callable=AsyncMock, return_value=_MOCK_RESULT):
            form = _stt_form(tiny_wav, provider=provider, model=model, **extra)
            resp = await user_client.post(
                STT_URL,
                data=form,
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["text"] == "Hello world"
        assert body["provider"] == provider
        assert body["model"] == model

    async def test_groq_default_model_is_turbo(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "groq"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.status_code == 200
        assert resp.json()["model"] == "whisper-large-v3-turbo"

    async def test_openai_default_model(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.openai.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "openai"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.json()["model"] == "gpt-4o-mini-transcribe"

    async def test_deepgram_default_model(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.deepgram.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "deepgram"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.json()["model"] == "nova-3"


# ── Model validation ──────────────────────────────────────────────────────────

class TestSTTModelValidation:

    async def test_invalid_model_for_groq_rejected(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "groq", "model": "nova-3"},  # Deepgram model
            files={"file": ("audio.wav", tiny_wav, "audio/wav")},
        )
        assert resp.status_code == 422

    async def test_invalid_model_for_spitch_rejected(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "spitch", "model": "whisper-large-v3", "language": "en"},
            files={"file": ("audio.wav", tiny_wav, "audio/wav")},
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("model", ["whisper-large-v3", "whisper-large-v3-turbo", "distil-whisper-large-v2"])
    async def test_all_groq_models_accepted(self, user_client: AsyncClient, tiny_wav: bytes, model: str):
        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "groq", "model": model},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.status_code == 200

    @pytest.mark.parametrize("model", ["nova-3", "nova-2", "enhanced", "base"])
    async def test_all_deepgram_models_accepted(self, user_client: AsyncClient, tiny_wav: bytes, model: str):
        with patch("app.services.stt.providers.deepgram.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "deepgram", "model": model},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.status_code == 200


# ── Language validation ───────────────────────────────────────────────────────

class TestSTTLanguageValidation:

    async def test_spitch_requires_language(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.spitch.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "spitch"},
                files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
            )
        assert resp.status_code == 400
        assert "language" in resp.json()["detail"].lower()

    async def test_spitch_rejects_unsupported_language(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "spitch", "language": "zh"},  # Chinese not supported
            files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("lang", ["en", "yo", "ha", "ig", "am"])
    async def test_spitch_accepts_all_supported_languages(
        self, user_client: AsyncClient, tiny_wav: bytes, lang: str
    ):
        with patch("app.services.stt.providers.spitch.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "spitch", "language": lang},
                files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
            )
        assert resp.status_code == 200

    async def test_intron_requires_language(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "intron"},
            files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("lang", ["sw", "ha", "yo", "ig", "am", "en", "zu", "af"])
    async def test_intron_accepts_all_supported_languages(
        self, user_client: AsyncClient, tiny_wav: bytes, lang: str
    ):
        with patch("app.services.stt.providers.intron.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "intron", "language": lang},
                files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
            )
        assert resp.status_code == 200

    async def test_deepgram_rejects_unknown_language(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "deepgram", "language": "xx-FAKE"},
            files={"file": ("audio.wav", tiny_wav, "audio/wav")},
        )
        assert resp.status_code == 400

    async def test_groq_accepts_without_language(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "groq"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert resp.status_code == 200


# ── File type validation ──────────────────────────────────────────────────────

class TestSTTFileValidation:

    async def test_unsupported_extension_rejected(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "groq"},
            files={"file": ("audio.txt", tiny_wav, "text/plain")},
        )
        assert resp.status_code == 400
        assert "type" in resp.json()["detail"].lower() or "allowed" in resp.json()["detail"].lower()

    async def test_spitch_rejects_wav_extension(self, user_client: AsyncClient, tiny_wav: bytes):
        # Spitch only accepts .mp3 .wav .m4a .ogg – WAV is actually allowed; test a rejected one
        resp = await user_client.post(
            STT_URL,
            data={"provider": "spitch", "language": "en"},
            files={"file": ("audio.aac", tiny_wav, "audio/aac")},
        )
        assert resp.status_code == 400

    async def test_missing_file_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(STT_URL, data={"provider": "groq"})
        assert resp.status_code == 422

    async def test_oversized_file_rejected(self, user_client: AsyncClient):
        big_bytes = b"\x00" * (51 * 1024 * 1024)  # 51 MB
        resp = await user_client.post(
            STT_URL,
            data={"provider": "groq"},
            files={"file": ("big.wav", big_bytes, "audio/wav")},
        )
        assert resp.status_code == 400
        assert "mb" in resp.json()["detail"].lower()


# ── Timestamp validation ──────────────────────────────────────────────────────

class TestSTTTimestamp:

    async def test_timestamp_on_unsupported_model_rejected(self, user_client: AsyncClient, tiny_wav: bytes):
        resp = await user_client.post(
            STT_URL,
            data={"provider": "spitch", "model": "legacy", "language": "en", "timestamp": "word"},
            files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
        )
        assert resp.status_code == 400

    async def test_timestamp_on_mansa_v1_accepted(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.spitch.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "spitch", "model": "mansa_v1", "language": "en", "timestamp": "word"},
                files={"file": ("audio.mp3", tiny_wav, "audio/mpeg")},
            )
        assert resp.status_code == 200


# ── Caching ───────────────────────────────────────────────────────────────────

class TestSTTCaching:

    async def test_identical_request_uses_cache_on_second_call(
        self, user_client: AsyncClient, tiny_wav: bytes, fake_redis
    ):
        mock_result = _MOCK_RESULT.copy()
        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=mock_result) as mock_fn:
            # First call – cache miss
            await user_client.post(
                STT_URL,
                data={"provider": "groq", "model": "whisper-large-v3-turbo"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
            assert mock_fn.call_count == 1

            # Second call – should hit cache, not call provider
            await user_client.post(
                STT_URL,
                data={"provider": "groq", "model": "whisper-large-v3-turbo"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
            assert mock_fn.call_count == 1  # still 1

    async def test_different_provider_different_cache_key(
        self, user_client: AsyncClient, tiny_wav: bytes
    ):
        groq_result = {"text": "groq result", "language": "en", "duration": 1.0}
        openai_result = {"text": "openai result", "language": "en", "duration": 1.0}

        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=groq_result), \
             patch("app.services.stt.providers.openai.transcribe", new_callable=AsyncMock, return_value=openai_result):
            r1 = await user_client.post(
                STT_URL, data={"provider": "groq"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
            r2 = await user_client.post(
                STT_URL, data={"provider": "openai"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        assert r1.json()["text"] == "groq result"
        assert r2.json()["text"] == "openai result"


# ── Authentication ────────────────────────────────────────────────────────────

class TestSTTAuthentication:

    async def test_unauthenticated_rejected(self, client: AsyncClient, tiny_wav: bytes):
        resp = await client.post(
            STT_URL,
            data={"provider": "groq"},
            files={"file": ("audio.wav", tiny_wav, "audio/wav")},
        )
        assert resp.status_code == 401

    async def test_response_schema(self, user_client: AsyncClient, tiny_wav: bytes):
        with patch("app.services.stt.providers.groq.transcribe", new_callable=AsyncMock, return_value=_MOCK_RESULT):
            resp = await user_client.post(
                STT_URL,
                data={"provider": "groq"},
                files={"file": ("audio.wav", tiny_wav, "audio/wav")},
            )
        body = resp.json()
        assert "text" in body
        assert "provider" in body
        assert "model" in body
