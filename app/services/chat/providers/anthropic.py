"""Chat provider – Anthropic Messages API."""

from __future__ import annotations

from app.config import get_config
from app.providers.anthropic import get_client


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    cfg = get_config()["llm"]["providers"]["anthropic"]
    client = get_client(cfg["api_key"])
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        **cfg.get("kwargs", {}),
        **kwargs,
    }
    if system:
        params["system"] = system
    response = await client.messages.create(**params)
    return response.content[0].text


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
):
    cfg = get_config()["llm"]["providers"]["anthropic"]
    client = get_client(cfg["api_key"])
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        **cfg.get("kwargs", {}),
        **kwargs,
    }
    if system:
        params["system"] = system
    async with client.messages.stream(**params) as stream:
        async for text in stream.text_stream:
            yield text
