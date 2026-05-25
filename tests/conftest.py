"""Shared pytest fixtures and helpers for the AI-DPI Middleware test suite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

# ── Test configuration constants ─────────────────────────────────────────────

TEST_JWT_SECRET = "test-secret-key-for-unit-tests"
TEST_JWT_ALGORITHM = "HS256"
TEST_CLIENT1_SECRET = "test-client1-secret"
TEST_CLIENT2_SECRET = "test-client2-secret"

TEST_CONFIG: dict[str, Any] = {
    "app": {"name": "AI DPI Middleware", "version": "0.1.0", "debug": False},
    "auth": {
        "issuers": [
            {
                "issuer": "test-local",
                "key": TEST_JWT_SECRET,
                "type": "local",
                "algorithm": "HS256",
                "client1": {"secret": TEST_CLIENT1_SECRET, "roles": ["user"]},
                "client2": {"secret": TEST_CLIENT2_SECRET, "roles": ["admin"]},
                "expire_minutes": 60,
            }
        ]
    },
    "llm": {
        "max_context_length": 131072,
        "max_new_tokens": 8192,
        "temperature": 0.9,
        "top_p": 0.95,
        "system_prompt_path": None,
        "rate_limit": {"user": 10, "admin": 60},
        "providers": {
            "anthropic": {"api_key": "test-anthropic-key", "default_model": "claude-sonnet-4-6", "max_tokens": 8096},
            "openai": {"api_key": "test-openai-key", "default_model": "gpt-4o", "max_tokens": 8096},
            "groq": {"api_key": "test-groq-key", "default_model": "llama-3.3-70b-versatile", "max_tokens": 8192},
            "gemini": {"api_key": "test-gemini-key", "default_model": "gemini-2.5-flash", "max_tokens": 8192},
        },
        "vector_database": {
            "provider": "weaviate",
            "type": "http",
            "http_host": "localhost",
            "http_port": 8080,
            "grpc_port": 50051,
            "N_RESULT": 2,
            "collection_name": "test_collection",
        },
        "embedding_model": {
            "model": "text-embedding-3-small",
            "provider": "openai",
            "API_KEY": "test-openai-key",
        },
    },
    "speech": {
        "max_file_size_mb": 50,
        "spitch_max_file_size_mb": 25,
        "providers": {
            "groq": {"api_key": "test-groq-key"},
            "openai": {"api_key": "test-openai-key"},
            "spitch": {"api_key": "test-spitch-key"},
            "deepgram": {"api_key": "test-deepgram-key"},
            "elevenlabs": {"api_key": "test-elevenlabs-key"},
            "intron": {"api_key": "test-intron-key", "base_url": "https://api.intron.africa/v1"},
        },
    },
    "stt": {"session_ttl_hours": 24, "rate_limit": {"user": 10, "admin": 60}},
    "tts": {"session_ttl_hours": 24, "rate_limit": {"user": 10, "admin": 60}},
    "redis": {"enabled": False, "url": "redis://localhost:6379/0"},
    "cors": {"allow_origins": ["*"], "allow_methods": ["*"], "allow_headers": ["*"], "allow_credentials": True},
    "document": {"pdf_folder": "./data/documents"},
    "logging": {"level": "INFO", "file": "log/app.log"},
}


# ── Fake Redis (in-memory) ────────────────────────────────────────────────────

class FakeRedis:
    """Minimal async Redis stub sufficient for rate limiting and caching tests."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._ttls: dict[str, float] = {}

    async def get(self, key: str) -> Any:
        return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        self._store[key] = value
        self._ttls[key] = ttl

    async def incr(self, key: str) -> int:
        self._store[key] = int(self._store.get(key, 0)) + 1
        return self._store[key]

    async def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._store.pop(k, None)
            self._ttls.pop(k, None)

    def clear(self) -> None:
        self._store.clear()
        self._ttls.clear()


# ── JWT helpers ───────────────────────────────────────────────────────────────

def make_token(roles: list[str], sub: str = "test-user", expires_in_minutes: int = 60) -> str:
    payload = {
        "sub": sub,
        "roles": roles,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


def user_token(sub: str = "user-001") -> str:
    return make_token(["user"], sub=sub)


def admin_token(sub: str = "admin-001") -> str:
    return make_token(["admin"], sub=sub)


def expired_token() -> str:
    return make_token(["user"], expires_in_minutes=-1)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_config():
    """Patch get_config everywhere so tests never touch the real YAML."""
    with patch("app.config.get_config", return_value=TEST_CONFIG), \
         patch("app.auth.oauth._auth_cfgs", TEST_CONFIG["auth"]["issuers"]), \
         patch("app.routers.v1.auth_route._auth_cfgs", TEST_CONFIG["auth"]["issuers"]):
        yield TEST_CONFIG


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture(autouse=True)
def patch_redis(fake_redis: FakeRedis):
    """Replace the Redis client with FakeRedis for all tests."""
    with patch("app.services.redis.get_client", return_value=fake_redis):
        yield fake_redis


@pytest.fixture(autouse=True)
def patch_embedding_and_vectordb():
    """Stub out the RAG pipeline (embedding + vector retrieval) for all tests.

    The chat route calls these unconditionally before any provider call.
    Tests that need to inspect RAG behaviour can override these stubs locally.
    """
    with patch(
        "app.services.embedding.main.get_embedding",
        new_callable=AsyncMock,
        return_value=[0.0] * 128,
    ), patch(
        "app.services.vectordb.main.retrieve",
        new_callable=AsyncMock,
        return_value="",
    ):
        yield


@pytest.fixture
def app() -> FastAPI:
    from app.main import app as _app
    return _app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    """Client with a valid user-role Bearer token pre-set."""
    client.headers["Authorization"] = f"Bearer {user_token()}"
    return client


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient) -> AsyncClient:
    """Client with a valid admin-role Bearer token pre-set."""
    client.headers["Authorization"] = f"Bearer {admin_token()}"
    return client


# ── Audio fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def tiny_wav() -> bytes:
    """Minimal valid WAV file (44-byte header, 1 sample of silence)."""
    import struct
    num_samples = 1
    sample_rate = 16000
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return header + b"\x00" * data_size
