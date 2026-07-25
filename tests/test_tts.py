"""Tests for the Text-to-Speech endpoint – providers, validation, caching."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

TTS_URL = "/api/v1/tts/synthesize"
_FAKE_AUDIO = b"RIFF\x00\x00\x00\x00WAVEfmt "  # Minimal WAV bytes


def _tts_body(
    text: str = "Hello, world!",
    provider: str = "groq",
    model: str = "playai-tts",
    voice: str | None = "Tara",
    language: str | None = None,
    response_format: str = "wav",
    speed: float = 1.0,
    instructions: str | None = None,
) -> dict:
    body: dict = {
        "text": text,
        "provider": provider,
        "model": model,
        "response_format": response_format,
        "speed": speed,
    }
    if voice is not None:
        body["voice"] = voice
    if language:
        body["language"] = language
    if instructions:
        body["instructions"] = instructions
    return body


# ── Provider routing ──────────────────────────────────────────────────────────

class TestTTSProviderRouting:

    @pytest.mark.parametrize("provider,model,extra", [
        ("groq", "playai-tts", {"voice": "Tara"}),
        ("openai", "tts-1", {"voice": "alloy"}),
        ("elevenlabs", "eleven_multilingual_v2", {"voice": "Rachel"}),
        ("spitch", "legacy", {"voice": "en-male-1", "language": "en"}),
        ("intron", "sahara-tts-v1", {"voice": "en-female-1", "language": "en"}),
    ])
    async def test_provider_routes_correctly(
        self,
        user_client: AsyncClient,
        provider: str,
        model: str,
        extra: dict,
    ):
        mock_path = f"app.services.tts.providers.{provider}.synthesize"
        with patch(mock_path, new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(
                TTS_URL,
                json=_tts_body(provider=provider, model=model, voice=None, **extra),
            )

        assert resp.status_code == 200, resp.text
        assert resp.content == _FAKE_AUDIO
        assert "audio" in resp.headers["content-type"]

    async def test_response_has_content_disposition(self, user_client: AsyncClient):
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(TTS_URL, json=_tts_body())
        assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_cache_miss_header(self, user_client: AsyncClient):
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(TTS_URL, json=_tts_body())
        assert resp.headers.get("X-Cache") == "MISS"

    async def test_cache_hit_header(self, user_client: AsyncClient, fake_redis):
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            await user_client.post(TTS_URL, json=_tts_body())  # populate cache
            resp = await user_client.post(TTS_URL, json=_tts_body())  # hit
        assert resp.headers.get("X-Cache") == "HIT"


# ── Schema validation ─────────────────────────────────────────────────────────

class TestTTSSchemaValidation:

    async def test_empty_text_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TTS_URL, json={**_tts_body(), "text": ""})
        assert resp.status_code == 422

    async def test_text_too_long_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TTS_URL, json={**_tts_body(), "text": "a" * 5001})
        assert resp.status_code == 422

    async def test_invalid_provider_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TTS_URL, json={**_tts_body(), "provider": "fakeprovider"})
        assert resp.status_code == 422

    async def test_model_incompatible_with_provider_rejected(self, user_client: AsyncClient):
        # Groq model passed to OpenAI provider
        resp = await user_client.post(
            TTS_URL,
            json=_tts_body(provider="openai", model="playai-tts", voice="alloy"),
        )
        assert resp.status_code == 422

    async def test_invalid_response_format_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={**_tts_body(), "response_format": "mp5"},  # not valid
        )
        assert resp.status_code == 422

    async def test_speed_out_of_range_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TTS_URL, json={**_tts_body(), "speed": 10.0})
        assert resp.status_code == 422

    @pytest.mark.parametrize("fmt", ["wav", "mp3", "flac", "aac", "opus", "pcm"])
    async def test_all_standard_formats_accepted(self, user_client: AsyncClient, fmt: str):
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(
                TTS_URL,
                json=_tts_body(response_format=fmt),
            )
        assert resp.status_code == 200


# ── Provider-specific rules ───────────────────────────────────────────────────

class TestTTSProviderRules:

    async def test_spitch_requires_voice(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={
                "text": "Hello",
                "provider": "spitch",
                "model": "legacy",
                "language": "en",
                "response_format": "wav",
            },
        )
        assert resp.status_code == 422

    async def test_spitch_requires_language(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={
                "text": "Hello",
                "provider": "spitch",
                "model": "legacy",
                "voice": "en-male-1",
                "response_format": "wav",
            },
        )
        assert resp.status_code == 422

    async def test_spitch_rejects_unsupported_language(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={
                "text": "Hello",
                "provider": "spitch",
                "model": "legacy",
                "voice": "en-male-1",
                "language": "zh",  # Not supported by Spitch TTS
                "response_format": "wav",
            },
        )
        assert resp.status_code == 422

    async def test_intron_requires_language(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={
                "text": "Hello",
                "provider": "intron",
                "model": "sahara-tts-v1",
                "voice": "en-female-1",
                "response_format": "wav",
            },
        )
        assert resp.status_code == 422

    async def test_instructions_only_for_gpt4o_mini_tts(self, user_client: AsyncClient):
        # instructions on tts-1 should fail
        resp = await user_client.post(
            TTS_URL,
            json=_tts_body(
                provider="openai",
                model="tts-1",
                voice="alloy",
                instructions="Speak slowly",
            ),
        )
        assert resp.status_code == 422

    async def test_instructions_accepted_on_gpt4o_mini_tts(self, user_client: AsyncClient):
        with patch("app.services.tts.providers.openai.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(
                TTS_URL,
                json=_tts_body(
                    provider="openai",
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    instructions="Speak slowly",
                ),
            )
        assert resp.status_code == 200

    async def test_elevenlabs_rejects_unsupported_language(self, user_client: AsyncClient):
        resp = await user_client.post(
            TTS_URL,
            json={
                "text": "Hello",
                "provider": "elevenlabs",
                "model": "eleven_multilingual_v2",
                "language": "xx-FAKE",
                "response_format": "wav",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("lang", ["en", "fr", "de", "es", "yo", "sw", "ha"])
    async def test_intron_accepts_supported_languages(self, user_client: AsyncClient, lang: str):
        with patch("app.services.tts.providers.intron.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await user_client.post(
                TTS_URL,
                json={
                    "text": "Hello",
                    "provider": "intron",
                    "model": "sahara-tts-v1",
                    "voice": f"{lang}-female-1",
                    "language": lang,
                    "response_format": "wav",
                },
            )
        assert resp.status_code == 200

    async def test_groq_all_models_accepted(self, user_client: AsyncClient):
        models = [
            ("playai-tts", "Tara"),
            ("playai-tts-arabic", "Tara"),
            ("canopylabs/orpheus-v1-english", "Autumn"),
        ]
        for model, voice in models:
            with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
                resp = await user_client.post(
                    TTS_URL,
                    json=_tts_body(provider="groq", model=model, voice=voice),
                )
            assert resp.status_code == 200, f"Model {model} failed: {resp.text}"


# ── Caching ───────────────────────────────────────────────────────────────────

class TestTTSCaching:

    async def test_provider_not_called_on_cache_hit(self, user_client: AsyncClient):
        body = _tts_body(text="Cache test sentence")
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO) as mock:
            await user_client.post(TTS_URL, json=body)
            await user_client.post(TTS_URL, json=body)
        assert mock.call_count == 1

    async def test_different_text_different_cache_entry(self, user_client: AsyncClient):
        audio1 = b"audio-one"
        audio2 = b"audio-two"
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock) as mock:
            mock.side_effect = [audio1, audio2]
            r1 = await user_client.post(TTS_URL, json=_tts_body(text="First sentence"))
            r2 = await user_client.post(TTS_URL, json=_tts_body(text="Second sentence"))
        assert r1.content == audio1
        assert r2.content == audio2


# ── Authentication ────────────────────────────────────────────────────────────

class TestTTSAuthentication:

    async def test_unauthenticated_rejected(self, client: AsyncClient):
        resp = await client.post(TTS_URL, json=_tts_body())
        assert resp.status_code == 401

    async def test_admin_can_access(self, admin_client: AsyncClient):
        with patch("app.services.tts.providers.groq.synthesize", new_callable=AsyncMock, return_value=_FAKE_AUDIO):
            resp = await admin_client.post(TTS_URL, json=_tts_body())
        assert resp.status_code == 200
