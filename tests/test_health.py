"""Tests for health check and landing page endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:

    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body

    async def test_health_no_auth_required(self, client: AsyncClient):
        # No Authorization header – should still return 200
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_landing_page_returns_html(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_landing_page_contains_app_name(self, client: AsyncClient):
        resp = await client.get("/")
        assert "AI" in resp.text and "Middleware" in resp.text

    async def test_landing_page_contains_api_docs_link(self, client: AsyncClient):
        resp = await client.get("/")
        assert "/docs" in resp.text

    async def test_landing_page_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code != 401

    async def test_openapi_schema_accessible(self, client: AsyncClient):
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "openapi" in schema
        assert "paths" in schema

    async def test_openapi_schema_contains_all_routes(self, client: AsyncClient):
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected = [
            "/api/v1/auth/token",
            "/api/v1/stt/transcribe",
            "/api/v1/tts/synthesize",
            "/api/v1/ai",
            "/api/v1/translate",
        ]
        for path in expected:
            assert path in paths, f"Route {path} missing from OpenAPI schema"

    async def test_docs_page_accessible(self, client: AsyncClient):
        resp = await client.get("/docs")
        assert resp.status_code == 200

    async def test_redoc_page_accessible(self, client: AsyncClient):
        resp = await client.get("/redoc")
        assert resp.status_code == 200
