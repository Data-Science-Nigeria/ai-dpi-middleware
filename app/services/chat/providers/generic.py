"""Chat provider – generic OpenAI-compatible API."""

from __future__ import annotations

import json

import aiohttp

from app.config import get_config


async def chat(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None = None,
    url: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    resolved = _build_messages(messages, system)
    cfg = get_config()["llm"]["providers"][provider]

    resolved_url = url or cfg["openai_url"]
    payload = {
        "model": model,
        "messages": resolved,
        "max_completion_tokens": max_tokens,
        **cfg.get("kwargs", {}),
        **kwargs,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            resolved_url, headers=_headers(cfg["api_key"]), json=payload
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["choices"][0]["message"]["content"]


async def stream_chat(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None = None,
    url: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
):
    resolved = _build_messages(messages, system)
    cfg = get_config()["llm"]["providers"][provider]

    resolved_url = url or cfg["openai_url"]
    payload = {
        "model": model,
        "messages": resolved,
        "max_completion_tokens": max_tokens,
        "stream": True,
        **cfg.get("kwargs", {}),
        **kwargs,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            resolved_url, headers=_headers(cfg["api_key"]), json=payload
        ) as response:
            response.raise_for_status()
            async for raw_line in response.content:
                line = raw_line.decode().strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError):
                    continue


def _headers(api_key: str) -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def _build_messages(messages: list, system: str | None) -> list:
    if system:
        return [{"role": "system", "content": system}, *messages]
    return list(messages)
