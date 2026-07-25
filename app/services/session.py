"""Session service – Redis-backed per-session conversation history."""

from __future__ import annotations

import json

from app.config import get_config
from app.services.redis import get_client


def _cfg() -> dict:
    return get_config().get("chat", {})


def _key(session_id: str) -> str:
    prefix = get_config().get("redis", {}).get("session_prefix", "session:")
    return f"{prefix}{session_id}:messages"


def _ttl_seconds() -> int:
    hours = _cfg().get("session_ttl_hours", 24)
    return int(hours * 3600)


def _history_limit() -> int:
    return int(_cfg().get("history_limit", 20))


async def get_history(session_id: str) -> list[dict]:
    """Return stored messages oldest-first. Empty list if none or Redis disabled."""
    try:
        client = get_client()
    except RuntimeError:
        return []

    raw: list[str] = await client.lrange(_key(session_id), 0, -1)
    return [json.loads(r) for r in raw]


async def append(session_id: str, role: str, content: str) -> None:
    """Append a message and enforce history_limit + TTL."""
    try:
        client = get_client()
    except RuntimeError:
        return  # Redis disabled – session history silently skipped

    key = _key(session_id)
    msg = json.dumps({"role": role, "content": content})

    pipe = client.pipeline()
    pipe.rpush(key, msg)
    pipe.ltrim(key, -_history_limit(), -1)   # keep only last N messages
    pipe.expire(key, _ttl_seconds())
    await pipe.execute()


async def clear(session_id: str) -> bool:
    """Delete session history. Returns True if key existed."""
    try:
        client = get_client()
    except RuntimeError:
        return False
    deleted = await client.delete(_key(session_id))
    return bool(deleted)


async def exists(session_id: str) -> bool:
    try:
        client = get_client()
    except RuntimeError:
        return False
    return bool(await client.exists(_key(session_id)))
