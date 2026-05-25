"""Tests for AuthMiddleware and rate-limiting logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import admin_token, expired_token, make_token, user_token


# ── AuthMiddleware ────────────────────────────────────────────────────────────

class TestAuthMiddleware:

    @pytest.mark.parametrize("path", [
        "/", "/health", "/healthz", "/docs", "/redoc",
        "/openapi.json", "/api/v1/auth/token",
    ])
    async def test_public_paths_skip_auth(self, client: AsyncClient, path: str):
        resp = await client.get(path)
        assert resp.status_code != 401

    async def test_protected_path_without_token_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/ai")
        assert resp.status_code == 401
        assert "detail" in resp.json()

    async def test_valid_user_token_passes_middleware(self, client: AsyncClient):
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="hi"):
            resp = await client.post(
                "/api/v1/ai",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
                headers={"Authorization": f"Bearer {user_token()}"},
            )
        assert resp.status_code == 200

    async def test_expired_token_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/ai",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers={"Authorization": f"Bearer {expired_token()}"},
        )
        assert resp.status_code == 401

    async def test_malformed_bearer_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/ai",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert resp.status_code == 401

    async def test_wrong_scheme_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/ai",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers={"Authorization": f"Basic {user_token()}"},
        )
        assert resp.status_code == 401

    async def test_session_cookie_accepted(self, client: AsyncClient):
        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="hi"):
            resp = await client.post(
                "/api/v1/ai",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
                cookies={"session_token": user_token()},
            )
        assert resp.status_code == 200

    async def test_request_state_populated_with_user_claims(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token(sub='u-999')}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("sub") == "u-999"
        assert "user" in body.get("roles", [])


# ── RBAC enforcement ──────────────────────────────────────────────────────────

class TestRBAC:

    async def test_user_role_blocked_from_admin_only_endpoint(self, user_client: AsyncClient):
        resp = await user_client.post(
            "/api/v1/ai/stream",
            json={"messages": [{"role": "user", "content": "Hi"}],
                  "provider": "anthropic", "model": "claude-sonnet-4-6"},
        )
        assert resp.status_code == 403

    async def test_admin_role_allowed_on_admin_only_endpoint(self, admin_client: AsyncClient):
        async def _fake_stream(**_):
            yield "chunk"

        with patch("app.services.chat.providers.anthropic.stream_chat", side_effect=_fake_stream):
            resp = await admin_client.post(
                "/api/v1/ai/stream",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
            )
        assert resp.status_code == 200

    async def test_token_with_no_roles_blocked(self, client: AsyncClient):
        token = make_token(roles=[])
        resp = await client.post(
            "/api/v1/ai",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── Rate limiting ─────────────────────────────────────────────────────────────

class TestRateLimiting:

    async def test_user_rate_limit_enforced(self, fake_redis, client: AsyncClient):
        import time
        token = user_token(sub="rate-test-user")
        window = int(time.time() // 60)
        fake_redis._store[f"ratelimit:chat:rate-test-user:{window}"] = 11

        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="hi"):
            resp = await client.post(
                "/api/v1/ai",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    async def test_admin_has_higher_rate_limit(self, fake_redis, client: AsyncClient):
        import time
        token = admin_token(sub="rate-admin-user")
        window = int(time.time() // 60)
        fake_redis._store[f"ratelimit:chat:rate-admin-user:{window}"] = 11

        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="hi"):
            resp = await client.post(
                "/api/v1/ai",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

    async def test_rate_limit_response_includes_retry_after(self, fake_redis, client: AsyncClient):
        import time
        token = user_token(sub="rl-retry-user")
        window = int(time.time() // 60)
        fake_redis._store[f"ratelimit:stt:rl-retry-user:{window}"] = 999

        resp = await client.post(
            "/api/v1/stt/transcribe",
            data={"provider": "groq"},
            files={"file": ("a.wav", b"\x00" * 100, "audio/wav")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"

    async def test_rate_limit_error_message_includes_limit(self, fake_redis, client: AsyncClient):
        import time
        token = user_token(sub="rl-msg-user")
        window = int(time.time() // 60)
        fake_redis._store[f"ratelimit:chat:rl-msg-user:{window}"] = 999

        resp = await client.post(
            "/api/v1/ai",
            json={"messages": [{"role": "user", "content": "Hi"}],
                  "provider": "anthropic", "model": "claude-sonnet-4-6"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert "10" in resp.json()["detail"]

    async def test_different_users_separate_buckets(self, fake_redis, client: AsyncClient):
        import time
        window = int(time.time() // 60)
        fake_redis._store[f"ratelimit:chat:user-a:{window}"] = 999

        with patch("app.services.chat.providers.anthropic.chat", new_callable=AsyncMock, return_value="ok"):
            resp = await client.post(
                "/api/v1/ai",
                json={"messages": [{"role": "user", "content": "Hi"}],
                      "provider": "anthropic", "model": "claude-sonnet-4-6"},
                headers={"Authorization": f"Bearer {user_token(sub='user-b')}"},
            )
        assert resp.status_code == 200
