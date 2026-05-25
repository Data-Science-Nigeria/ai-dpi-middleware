"""Tests for the translation endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

TRANSLATE_URL = "/api/v1/translate"


def _body(
    text: str = "Hello, world!",
    target_language: str = "fr",
    source_language: str | None = None,
    provider: str = "anthropic",
    model: str | None = None,
    max_tokens: int = 512,
) -> dict:
    body: dict = {
        "text": text,
        "target_language": target_language,
        "provider": provider,
        "max_tokens": max_tokens,
    }
    if source_language:
        body["source_language"] = source_language
    if model:
        body["model"] = model
    return body


# ── Happy path — each provider ────────────────────────────────────────────────

class TestTranslateProviderRouting:

    @pytest.mark.parametrize("provider,model", [
        ("anthropic", "claude-sonnet-4-6"),
        ("openai", "gpt-4o"),
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.5-flash"),
    ])
    async def test_routes_to_provider(
        self, user_client: AsyncClient, provider: str, model: str
    ):
        with patch(
            f"app.services.chat.providers.{provider}.chat",
            new_callable=AsyncMock,
            return_value="  Bonjour, monde!  ",
        ):
            resp = await user_client.post(
                TRANSLATE_URL, json=_body(provider=provider, model=model)
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["translation"] == "Bonjour, monde!"  # stripped
        assert body["provider"] == provider
        assert body["model"] == model
        assert body["target_language"] == "fr"

    async def test_uses_default_model_when_omitted(self, user_client: AsyncClient):
        with patch(
            "app.services.chat.providers.anthropic.chat",
            new_callable=AsyncMock,
            return_value="Bonjour",
        ):
            resp = await user_client.post(
                TRANSLATE_URL, json=_body(provider="anthropic")
            )
        assert resp.status_code == 200
        assert resp.json()["model"] == "claude-sonnet-4-6"

    async def test_source_language_reflected_in_response(self, user_client: AsyncClient):
        with patch(
            "app.services.chat.providers.anthropic.chat",
            new_callable=AsyncMock,
            return_value="Bonjour",
        ):
            resp = await user_client.post(
                TRANSLATE_URL,
                json=_body(source_language="en", target_language="fr"),
            )
        assert resp.json()["source_language"] == "en"
        assert resp.json()["target_language"] == "fr"

    async def test_no_source_language_returns_none(self, user_client: AsyncClient):
        with patch(
            "app.services.chat.providers.anthropic.chat",
            new_callable=AsyncMock,
            return_value="Bonjour",
        ):
            resp = await user_client.post(
                TRANSLATE_URL, json=_body(source_language=None)
            )
        assert resp.json()["source_language"] is None


# ── Prompt engineering ────────────────────────────────────────────────────────

class TestTranslatePrompt:

    async def test_prompt_includes_target_language(self, user_client: AsyncClient):
        captured = {}

        async def _mock_chat(messages, **kwargs):
            captured["prompt"] = messages[0]["content"]
            return "Hola"

        with patch("app.services.chat.providers.anthropic.chat", side_effect=_mock_chat):
            await user_client.post(
                TRANSLATE_URL,
                json=_body(target_language="es", provider="anthropic", model="claude-sonnet-4-6"),
            )

        assert "es" in captured["prompt"] or "Spanish" in captured["prompt"]
        assert "Hello, world!" in captured["prompt"]

    async def test_prompt_includes_source_when_provided(self, user_client: AsyncClient):
        captured = {}

        async def _mock_chat(messages, **kwargs):
            captured["prompt"] = messages[0]["content"]
            return "Hola"

        with patch("app.services.chat.providers.anthropic.chat", side_effect=_mock_chat):
            await user_client.post(
                TRANSLATE_URL,
                json=_body(source_language="en", target_language="es", provider="anthropic", model="claude-sonnet-4-6"),
            )

        assert "en" in captured["prompt"] or "from" in captured["prompt"].lower()

    async def test_prompt_has_no_explanation_instruction(self, user_client: AsyncClient):
        captured = {}

        async def _mock_chat(messages, **kwargs):
            captured["prompt"] = messages[0]["content"]
            return "Hola"

        with patch("app.services.chat.providers.anthropic.chat", side_effect=_mock_chat):
            await user_client.post(
                TRANSLATE_URL,
                json=_body(provider="anthropic", model="claude-sonnet-4-6"),
            )

        prompt = captured["prompt"].lower()
        assert "no explanation" in prompt or "only the translated" in prompt


# ── Request validation ────────────────────────────────────────────────────────

class TestTranslateValidation:

    async def test_empty_text_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TRANSLATE_URL, json=_body(text=""))
        assert resp.status_code == 422

    async def test_text_too_long_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TRANSLATE_URL, json=_body(text="x" * 10001))
        assert resp.status_code == 422

    async def test_missing_target_language_rejected(self, user_client: AsyncClient):
        body = _body()
        del body["target_language"]
        resp = await user_client.post(TRANSLATE_URL, json=body)
        assert resp.status_code == 422

    async def test_invalid_provider_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TRANSLATE_URL, json={**_body(), "provider": "fake"})
        assert resp.status_code == 422

    async def test_max_tokens_too_large_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TRANSLATE_URL, json=_body(max_tokens=99999))
        assert resp.status_code == 422

    async def test_max_tokens_zero_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(TRANSLATE_URL, json=_body(max_tokens=0))
        assert resp.status_code == 422


# ── African language pairs ────────────────────────────────────────────────────

class TestTranslateAfricanLanguages:

    @pytest.mark.parametrize("target,provider,model", [
        ("yo", "anthropic", "claude-sonnet-4-6"),
        ("ha", "gemini", "gemini-2.5-flash"),
        ("sw", "openai", "gpt-4o"),
        ("ig", "groq", "llama-3.3-70b-versatile"),
        ("am", "anthropic", "claude-sonnet-4-6"),
    ])
    async def test_african_target_language_accepted(
        self, user_client: AsyncClient, target: str, provider: str, model: str
    ):
        with patch(
            f"app.services.chat.providers.{provider}.chat",
            new_callable=AsyncMock,
            return_value="translated",
        ):
            resp = await user_client.post(
                TRANSLATE_URL,
                json=_body(target_language=target, provider=provider, model=model),
            )
        assert resp.status_code == 200
        assert resp.json()["target_language"] == target


# ── Authentication ────────────────────────────────────────────────────────────

class TestTranslateAuthentication:

    async def test_unauthenticated_rejected(self, client: AsyncClient):
        resp = await client.post(TRANSLATE_URL, json=_body())
        assert resp.status_code == 401

    async def test_translation_stripped_of_whitespace(self, user_client: AsyncClient):
        with patch(
            "app.services.chat.providers.anthropic.chat",
            new_callable=AsyncMock,
            return_value="\n  Bonjour  \n",
        ):
            resp = await user_client.post(
                TRANSLATE_URL,
                json=_body(provider="anthropic", model="claude-sonnet-4-6"),
            )
        assert resp.json()["translation"] == "Bonjour"
