"""Async Redis client."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import get_config

_client: aioredis.Redis | None = None
_cfg = get_config()

def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(_cfg['redis']['url'], decode_responses=True)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
