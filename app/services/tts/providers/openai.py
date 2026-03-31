"""TTS provider — OpenAI audio API."""

from __future__ import annotations

import asyncio

from app.providers.openai import get_client
from app.services.tts.models.openai import (
    DEFAULT_VOICE,
    OPENAI_INSTRUCTIONS_MODELS,
    OPENAI_MAX_CHARS,
    OPENAI_SPEED_MAX,
    OPENAI_SPEED_MIN,
)


async def synthesize(
    text: str,
    voice: str | None = None,
    model: str = "tts-1",
    response_format: str = "mp3",
    speed: float = 1.0,
    instructions: str | None = None,
) -> bytes:
    """Run OpenAI audio.speech.create in a thread and return raw audio bytes.

    - All models accept up to 4096 characters.
    - `speed` ranges from 0.25 to 4.0 (default 1.0).
    - `instructions` is only honoured by `gpt-4o-mini-tts`.
    """
    if len(text) > OPENAI_MAX_CHARS:
        raise ValueError(
            f"OpenAI TTS accepts at most {OPENAI_MAX_CHARS} characters; got {len(text)}."
        )

    if not (OPENAI_SPEED_MIN <= speed <= OPENAI_SPEED_MAX):
        raise ValueError(
            f"`speed` must be between {OPENAI_SPEED_MIN} and {OPENAI_SPEED_MAX}; got {speed}."
        )

    resolved_voice = voice or DEFAULT_VOICE.get(model, "alloy")

    kwargs: dict = {
        "model": model,
        "voice": resolved_voice,
        "input": text,
        "response_format": response_format,
        "speed": speed,
    }

    if instructions is not None:
        if model not in OPENAI_INSTRUCTIONS_MODELS:
            raise ValueError(
                f"`instructions` is only supported by {sorted(OPENAI_INSTRUCTIONS_MODELS)}; "
                f"model '{model}' does not support it."
            )
        kwargs["instructions"] = instructions

    client = get_client()
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.audio.speech.create(**kwargs),
    )
    return response.read()
