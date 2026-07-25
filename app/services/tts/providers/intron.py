"""TTS provider – Intron (Sahara African-language models).

Intron has no official Python SDK; we use httpx directly.
API reference: https://docs.intron.africa
"""

from __future__ import annotations

import httpx

from app.providers.intron import get_api_key, get_base_url
from app.services.tts.models.intron import DEFAULT_VOICE, INTRON_TTS_LANGUAGES

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


async def synthesize(
    text: str,
    voice: str | None = None,
    model: str = "sahara-tts-v1",
    language: str = "en",
    response_format: str = "wav",
) -> bytes:
    """Generate speech using Intron's Sahara TTS API.

    Args:
        text:            Text to synthesize.
        voice:           Voice ID (e.g. sw-female-1). Defaults per language.
        model:           Intron TTS model: sahara-tts-v1.
        language:        Required BCP-47 code: sw, ha, yo, ig, am, en.
        response_format: Audio format: wav, mp3.
    """
    if language not in INTRON_TTS_LANGUAGES:
        raise ValueError(
            f"Intron TTS requires a supported language. "
            f"Supported: {sorted(INTRON_TTS_LANGUAGES)}."
        )

    resolved_voice = voice or DEFAULT_VOICE.get(model, "default")

    url = f"{get_base_url()}/speech/synthesize"
    headers = {"Authorization": f"Bearer {get_api_key()}"}

    payload = {
        "text": text,
        "model": model,
        "language": language,
        "voice": resolved_voice,
        "format": response_format,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    return response.content
