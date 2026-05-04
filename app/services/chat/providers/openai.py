"""Chat provider — OpenAI Chat Completions API."""

from __future__ import annotations

import asyncio
from functools import partial

from app.providers.openai import get_client
from app.services.chat.models.openai import OPENAI_REASONING_MODELS


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    resolved = _build_messages(messages, model, system)
    client = get_client()
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        partial(
            client.chat.completions.create,
            model=model,
            messages=resolved,
            max_tokens=max_tokens,
        ),
    )
    return response.choices[0].message.content


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
):
    if model in OPENAI_REASONING_MODELS:
        raise ValueError(
            f"Streaming is not supported for reasoning model '{model}'."
        )
    resolved = _build_messages(messages, model, system)
    client = get_client()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _stream_sync():
        stream = client.chat.completions.create(
            model=model,
            messages=resolved,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                loop.call_soon_threadsafe(queue.put_nowait, delta)
        loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _stream_sync)

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item


def _build_messages(
    messages: list[dict], model: str, system: str | None
) -> list[dict]:
    result = []
    if system and model not in OPENAI_REASONING_MODELS:
        result.append({"role": "system", "content": system})
    result.extend(messages)
    return result
