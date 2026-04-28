"""Async Redis client."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import get_config

_client: aioredis.Redis | None = None
_cfg = get_config().get('redis', {})  # type: ignore

def get_client() -> aioredis.Redis:
    if _cfg.get('enabled', False) is False:  # type: ignore
        raise RuntimeError("Redis is disabled in the configuration.")
    global _client
    if _client is None:
        _client = aioredis.from_url(_cfg['url'], decode_responses=True)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
