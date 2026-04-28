"""STT provider — OpenAI Whisper / GPT-4o transcription API."""

from __future__ import annotations

import asyncio

from app.providers.openai import get_client


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    model: str = "gpt-4o-mini-transcribe",
    language: str | None = None,
    prompt: str | None = None,
) -> dict:
    """Transcribe audio using OpenAI's transcription endpoint.

    Returns a dict with at minimum ``text``, plus ``language`` and
    ``duration`` when the API supplies them.
    """
    client = get_client()
    loop = asyncio.get_event_loop()

    kwargs: dict = {
        "file": (filename, file_bytes, content_type),
        "model": model,
        "response_format": "verbose_json",
        "temperature": 0.0,
    }
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt

    result = await loop.run_in_executor(
        None,
        lambda: client.audio.transcriptions.create(**kwargs),
    )

    return {
        "text": result.text,
        "language": getattr(result, "language", language),
        "duration": getattr(result, "duration", None),
    }
