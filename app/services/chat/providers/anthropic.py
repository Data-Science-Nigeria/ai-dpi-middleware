"""Chat provider — Anthropic Messages API."""

from __future__ import annotations

from app.config import get_config
from app.providers.anthropic import get_client


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    cfg = get_config()
    client = get_client(cfg["llm_provider"]["anthropic"]["api_key"])
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    response = await client.messages.create(**kwargs)
    return response.content[0].text


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
):
    cfg = get_config()
    client = get_client(cfg["llm_provider"]["anthropic"]["api_key"])
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text
