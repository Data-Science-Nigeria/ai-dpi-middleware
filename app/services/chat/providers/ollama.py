"""Ollama chat provider – sovereign / local LLM deployment (no external API calls)."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.config import get_config


def _cfg() -> dict:
    return get_config()["llm"]["providers"]["ollama"]


def _base_url() -> str:
    return _cfg().get("base_url", "http://localhost:11434")


def _build_messages(
    messages: list[dict],
    system: str | None,
) -> list[dict]:
    if system:
        return [{"role": "system", "content": system}, *messages]
    return messages


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    cfg = _cfg()
    payload = {
        "model": model,
        "messages": _build_messages(messages, system),
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            **cfg.get("options", {}),
        },
    }

    async with httpx.AsyncClient(timeout=cfg.get("timeout_seconds", 120.0)) as client:
        resp = await client.post(f"{_base_url()}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
) -> AsyncIterator[str]:
    cfg = _cfg()
    payload = {
        "model": model,
        "messages": _build_messages(messages, system),
        "stream": True,
        "options": {
            "num_predict": max_tokens,
            **cfg.get("options", {}),
        },
    }

    async with httpx.AsyncClient(timeout=cfg.get("timeout_seconds", 120.0)) as client:
        async with client.stream("POST", f"{_base_url()}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if content := data.get("message", {}).get("content"):
                    yield content
                if data.get("done"):
                    break
