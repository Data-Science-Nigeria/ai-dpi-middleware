"""Tests for authentication – token issuance, validation, and RBAC."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_CLIENT1_SECRET,
    TEST_CLIENT2_SECRET,
    TEST_JWT_SECRET,
    admin_token,
    expired_token,
    make_token,
    user_token,
)


# ── Token issuance (/api/v1/auth/token) ──────────────────────────────────────

class TestTokenIssuance:
    async def test_user_credentials_return_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "client1", "password": TEST_CLIENT1_SECRET},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert "user" in body["roles"]
        assert body["expires_in"] > 0

    async def test_admin_credentials_return_admin_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "client2", "password": TEST_CLIENT2_SECRET},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "admin" in body["roles"]

    async def test_wrong_password_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "client1", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    async def test_unknown_client_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "unknown_client", "password": "any-secret"},
        )
        assert resp.status_code == 401

    async def test_issued_token_is_valid_jwt(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "client1", "password": TEST_CLIENT1_SECRET},
        )
        token = resp.json()["access_token"]
        from jose import jwt
        claims = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert claims["roles"] == ["user"]
        assert "exp" in claims

    async def test_token_contains_correct_expiry(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "client1", "password": TEST_CLIENT1_SECRET},
        )
        assert resp.json()["expires_in"] == 60 * 60  # 60 minutes in seconds


# ── /api/v1/auth/me ──────────────────────────────────────────────────────────

class TestVerifyMe:
    async def test_me_returns_claims_for_valid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token()}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "user" in body.get("roles", [])

    async def test_me_rejects_missing_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_rejects_expired_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token()}"},
        )
        assert resp.status_code == 401

    async def test_me_rejects_malformed_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert resp.status_code == 401

    async def test_me_rejects_wrong_signature(self, client: AsyncClient):
        bad_token = make_token(["user"])
        # Tamper with signature
        parts = bad_token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        tampered = ".".join(parts)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401


# ── Protected route RBAC ─────────────────────────────────────────────────────

class TestProtectedRoute:
    async def test_user_can_access_protected_route(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/protected_route",
            headers={"Authorization": f"Bearer {user_token()}"},
        )
        assert resp.status_code == 200

    async def test_unauthenticated_blocked_from_protected_route(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/protected_route")
        assert resp.status_code == 401


# ── Public paths bypass auth ──────────────────────────────────────────────────

class TestPublicPaths:
    @pytest.mark.parametrize("path", ["/", "/health", "/docs", "/redoc", "/openapi.json"])
    async def test_public_paths_need_no_token(self, client: AsyncClient, path: str):
        resp = await client.get(path)
        # Any non-401 response is acceptable
        assert resp.status_code != 401
