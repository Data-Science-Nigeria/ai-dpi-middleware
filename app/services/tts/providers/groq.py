"""TTS provider — Groq audio API (Orpheus + PlayAI)."""

from __future__ import annotations

import asyncio
from functools import partial

from app.providers.groq import get_client
from app.services.tts.models.groq import (
    DEFAULT_VOICE,
    ORPHEUS_MAX_CHARS,
    ORPHEUS_MODELS,
)


async def synthesize(
    text: str,
    voice: str | None = None,
    model: str = "playai-tts",
    response_format: str = "wav",
) -> bytes:
    """Run Groq audio.speech.create in a thread and return raw audio bytes.

    Orpheus models (canopylabs/*) are limited to 200 characters per request.
    The English Orpheus model supports inline vocal-direction tags, e.g.:
        "Hello! [cheerful] Welcome to the service."
    """
    if model in ORPHEUS_MODELS and len(text) > ORPHEUS_MAX_CHARS:
        raise ValueError(
            f"Orpheus models accept at most {ORPHEUS_MAX_CHARS} characters; "
            f"got {len(text)}."
        )

    resolved_voice = voice or DEFAULT_VOICE.get(model, "Tara")

    client = get_client()
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        partial(
            client.audio.speech.create,
            model=model,
            voice=resolved_voice,
            input=text,
            response_format=response_format,  # type: ignore[arg-type]
        ),
    )
    return response.read()
