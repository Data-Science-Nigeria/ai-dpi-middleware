"""TTS provider — Spitch speech generation API."""

from __future__ import annotations

import asyncio
from functools import partial

from app.providers.spitch import get_client
from app.services.tts.models.spitch import SPITCH_TTS_LANGUAGES


async def synthesize(
    text: str,
    voice: str,
    language: str,
    model: str = "legacy",
    response_format: str = "wav",
) -> bytes:
    """Generate speech using the Spitch API.

    Args:
        text:            Text to synthesize.
        voice:           Voice ID (see docs.spitch.app/concepts/voices for full list).
        language:        Required language code: en, ha, ig, yo.
        model:           TTS model — currently only ``legacy``.
        response_format: Audio format: wav, mp3, ogg_opus, webm_opus, flac, pcm_s16le, mulaw, alaw.
    """
    if language not in SPITCH_TTS_LANGUAGES:
        raise ValueError(
            f"Spitch TTS requires a language. "
            f"Supported: {sorted(SPITCH_TTS_LANGUAGES)}."
        )

    client = get_client()
    loop = asyncio.get_event_loop()

    response = await loop.run_in_executor(
        None,
        partial(
            client.speech.generate,
            text=text,
            language=language,
            voice=voice,
            model=model,
            format=response_format,
        ),
    )
    return response.read()
