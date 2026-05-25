"""Tests for the LLM chat endpoint — provider routing, validation, streaming."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import admin_token, user_token

CHAT_URL = "/api/v1/ai"


def _chat_body(
    messages: list[dict] | None = None,
    provider: str = "anthropic",
    model: str | None = None,
    max_tokens: int = 256,
    system: str | None = None,
) -> dict:
    body: dict = {
        "messages": messages or [{"role": "user", "content": "Hello"}],
        "provider": provider,
        "max_tokens": max_tokens,
    }
    if model:
        body["model"] = model
    if system:
        body["system"] = system
    return body


# ── Happy path — each provider ────────────────────────────────────────────────

class TestChatProviderRouting:
    """Each provider is mocked; embedding/vectordb are stubbed by conftest."""

    @pytest.mark.parametrize("provider,model", [
        ("anthropic", "claude-sonnet-4-6"),
        ("openai", "gpt-4o"),
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.5-flash"),
    ])
    async def test_chat_routes_to_correct_provider(
        self, user_client: AsyncClient, provider: str, model: str
    ):
        with patch(f"app.services.chat.providers.{provider}.chat", new_callable=AsyncMock, return_value="Mocked reply"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider=provider, model=model))

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["reply"] == "Mocked reply"
        assert body["provider"] == provider
        assert body["model"] == model

    async def test_chat_anthropic_default_model(self, user_client: AsyncClient):
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="Hi"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="anthropic"))
        assert resp.status_code == 200
        assert resp.json()["model"] == "claude-sonnet-4-6"

    async def test_chat_openai_default_model(self, user_client: AsyncClient):
        with patch("app.services.chat.providers.openai.chat", new_callable=AsyncMock, return_value="Hi"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="openai"))
        assert resp.json()["model"] == "gpt-4o"

    async def test_chat_groq_default_model(self, user_client: AsyncClient):
        with patch("app.services.chat.providers.groq.chat", new_callable=AsyncMock, return_value="Hi"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="groq"))
        assert resp.json()["model"] == "llama-3.3-70b-versatile"

    async def test_chat_gemini_default_model(self, user_client: AsyncClient):
        with patch("app.services.chat.providers.gemini.chat", new_callable=AsyncMock, return_value="Hi"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="gemini"))
        assert resp.json()["model"] == "gemini-2.5-flash"


# ── Model validation ──────────────────────────────────────────────────────────

class TestChatModelValidation:
    async def test_invalid_model_for_provider_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            CHAT_URL,
            json=_chat_body(provider="anthropic", model="gpt-4o"),
        )
        assert resp.status_code == 422

    async def test_invalid_provider_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            CHAT_URL,
            json={**_chat_body(), "provider": "unknown-provider"},
        )
        assert resp.status_code == 422

    async def test_empty_messages_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(CHAT_URL, json=_chat_body(messages=[]))
        assert resp.status_code == 422

    async def test_invalid_role_in_message_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            CHAT_URL,
            json=_chat_body(messages=[{"role": "system", "content": "Hi"}]),
        )
        assert resp.status_code == 422

    async def test_max_tokens_too_large_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            CHAT_URL,
            json=_chat_body(provider="anthropic", model="claude-sonnet-4-6", max_tokens=99999),
        )
        assert resp.status_code == 422

    async def test_max_tokens_zero_rejected(self, user_client: AsyncClient):
        resp = await user_client.post(
            CHAT_URL,
            json=_chat_body(provider="anthropic", model="claude-sonnet-4-6", max_tokens=0),
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("model", [
        "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
    ])
    async def test_all_anthropic_models_accepted(self, user_client: AsyncClient, model: str):
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="ok"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="anthropic", model=model))
        assert resp.status_code == 200

    @pytest.mark.parametrize("model", [
        "gpt-4o", "gpt-4o-mini", "gpt-5", "gpt-5-mini", "o1", "o3", "o3-mini", "o4-mini",
    ])
    async def test_all_openai_models_accepted(self, user_client: AsyncClient, model: str):
        with patch("app.services.chat.providers.openai.chat", new_callable=AsyncMock, return_value="ok"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="openai", model=model))
        assert resp.status_code == 200

    @pytest.mark.parametrize("model", [
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
        "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash",
    ])
    async def test_all_gemini_models_accepted(self, user_client: AsyncClient, model: str):
        with patch("app.services.chat.providers.gemini.chat", new_callable=AsyncMock, return_value="ok"):
            resp = await user_client.post(CHAT_URL, json=_chat_body(provider="gemini", model=model))
        assert resp.status_code == 200


# ── Auth enforcement ──────────────────────────────────────────────────────────

class TestChatAuthentication:
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        resp = await client.post(CHAT_URL, json=_chat_body())
        assert resp.status_code == 401

    async def test_user_role_can_access_chat(self, user_client: AsyncClient):
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="Hi"):
            resp = await user_client.post(
                CHAT_URL, json=_chat_body(provider="anthropic", model="claude-sonnet-4-6")
            )
        assert resp.status_code == 200


# ── Streaming endpoint (/api/v1/ai/stream) ────────────────────────────────────

class TestChatStream:
    async def test_stream_requires_admin(self, user_client: AsyncClient):
        resp = await user_client.post(
            f"{CHAT_URL}/stream",
            json=_chat_body(provider="anthropic", model="claude-sonnet-4-6"),
        )
        assert resp.status_code == 403

    async def test_stream_works_for_admin(self, admin_client: AsyncClient):
        async def _fake_stream(**_):
            for chunk in ["Hello", " World"]:
                yield chunk

        with patch("app.services.chat.providers.anthropic.stream_chat", side_effect=_fake_stream):
            resp = await admin_client.post(
                f"{CHAT_URL}/stream",
                json=_chat_body(provider="anthropic", model="claude-sonnet-4-6"),
            )
        assert resp.status_code == 200
        assert "Hello" in resp.text

    async def test_stream_unauthenticated_rejected(self, client: AsyncClient):
        resp = await client.post(
            f"{CHAT_URL}/stream",
            json=_chat_body(provider="anthropic", model="claude-sonnet-4-6"),
        )
        assert resp.status_code == 401


# ── Multi-turn conversations ──────────────────────────────────────────────────

class TestChatMultiTurn:
    async def test_multi_turn_messages_accepted(self, user_client: AsyncClient):
        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "What about 3+3?"},
        ]
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="6"):
            resp = await user_client.post(
                CHAT_URL,
                json=_chat_body(messages=messages, provider="anthropic", model="claude-sonnet-4-6"),
            )
        assert resp.status_code == 200
        assert resp.json()["reply"] == "6"
