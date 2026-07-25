"""STT provider – Intron (Sahara African-language models).

Intron has no official Python SDK; we use httpx directly.
API reference: https://docs.intron.africa
"""

from __future__ import annotations

import httpx

from app.providers.intron import get_api_key, get_base_url
from app.services.stt.models.intron import DEFAULT_MODEL

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    model: str = DEFAULT_MODEL,
    language: str = "en",
    special_words: str | None = None,
    timestamp: str = "none",
) -> dict:
    """Transcribe audio using Intron's Sahara STT API.

    Args:
        file_bytes:    Raw audio bytes.
        filename:      Original filename – used as the multipart filename.
        content_type:  MIME type of the audio file.
        model:         Intron model: sahara-v1.
        language:      Required BCP-47 code: sw, ha, yo, ig, am, so, zu, xh, af, wo, ff, en.
        special_words: Custom vocabulary hint to boost recognition accuracy.
        timestamp:     ``none`` | ``word`` | ``segment``.
    """
    url = f"{get_base_url()}/speech/transcribe"
    headers = {"Authorization": f"Bearer {get_api_key()}"}

    data: dict = {
        "model": model,
        "language": language,
        "timestamp": timestamp,
    }
    if special_words:
        data["special_words"] = special_words

    files = {"file": (filename, file_bytes, content_type)}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, data=data, files=files)
        response.raise_for_status()
        body = response.json()

    return {
        "text": body.get("transcript") or body.get("text", ""),
        "language": body.get("language", language),
        "duration": body.get("duration"),
    }
