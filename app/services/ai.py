"""Async wrapper around the Anthropic client."""

from __future__ import annotations
from app.config import settings
from app.providers.anthropic import get_client


async def chat(messages: list[dict], system: str | None = None, max_tokens: int = 1024) -> str:
    """Send a chat request and return the text response."""
    client = get_client()
    kwargs: dict = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)
    return response.content[0].text


async def stream_chat(messages: list[dict], system: str | None = None, max_tokens: int = 1024):
    """Async generator that yields text chunks as they arrive."""
    client = get_client()
    kwargs: dict = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text