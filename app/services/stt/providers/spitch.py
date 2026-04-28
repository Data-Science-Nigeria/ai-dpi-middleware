"""STT provider — Spitch transcription API."""

from __future__ import annotations

import asyncio
from functools import partial

from app.providers.spitch import get_client


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    model: str = "legacy",
    language: str = "en",
    special_words: str | None = None,
    timestamp: str = "none",
) -> dict:
    """Transcribe audio using the Spitch API.

    Args:
        file_bytes:    Raw audio bytes.
        filename:      Original filename (used for logging/debug only).
        content_type:  MIME type of the audio file.
        model:         ``legacy`` or ``mansa_v1``.
        language:      Required ISO-639-1 code: en, yo, ha, ig, am.
        special_words: Custom vocabulary hint to boost recognition accuracy.
        timestamp:     ``none`` | ``sentence`` | ``word``. Only ``mansa_v1`` supports this.
    """
    client = get_client()
    loop = asyncio.get_event_loop()

    kwargs: dict = {
        "content": file_bytes,
        "language": language,
        "model": model,
        "timestamp": timestamp,
    }
    if special_words:
        kwargs["special_words"] = special_words

    result = await loop.run_in_executor(
        None,
        partial(client.speech.transcribe, **kwargs),
    )

    return {
        "text": result.text,
        "language": language,
        "duration": None,
        "request_id": getattr(result, "request_id", None),
    }
