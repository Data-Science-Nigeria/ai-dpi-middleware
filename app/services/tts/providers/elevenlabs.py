"""TTS provider – ElevenLabs.

Supports 32 languages with eleven_multilingual_v2 and flash/turbo variants.
"""

from __future__ import annotations

import asyncio
from functools import partial

from app.providers.elevenlabs import get_client
from app.services.tts.models.elevenlabs import DEFAULT_VOICE, FORMAT_MAP


async def synthesize(
    text: str,
    voice: str | None = None,
    model: str = "eleven_multilingual_v2",
    response_format: str = "mp3",
    language_code: str | None = None,
) -> bytes:
    """Generate speech using ElevenLabs.

    Args:
        text:            Text to synthesize.
        voice:           Voice name (e.g. Rachel, Bella). Defaults to Rachel.
        model:           ElevenLabs model ID.
        response_format: Common format name: mp3, pcm, wav, ulaw, mulaw.
        language_code:   BCP-47 code to lock the output language (optional).
                         When None, ElevenLabs auto-detects from the text.
    """
    client = get_client()
    resolved_voice = voice or DEFAULT_VOICE.get(model, "Rachel")
    output_format = FORMAT_MAP.get(response_format, "mp3_44100_128")

    kwargs: dict = {
        "voice_id": resolved_voice,
        "text": text,
        "model_id": model,
        "output_format": output_format,
    }
    if language_code:
        kwargs["language_code"] = language_code

    loop = asyncio.get_event_loop()
    audio_iter = await loop.run_in_executor(
        None,
        partial(client.text_to_speech.convert, **kwargs),
    )

    return b"".join(audio_iter)


async def stream_synthesize(
    text: str,
    voice: str | None = None,
    model: str = "eleven_multilingual_v2",
    response_format: str = "mp3",
    language_code: str | None = None,
    chunk_size: int = 4096,
):
    """Yield audio chunks via ElevenLabs convert_as_stream."""
    client = get_client()
    resolved_voice = voice or DEFAULT_VOICE.get(model, "Rachel")
    output_format = FORMAT_MAP.get(response_format, "mp3_44100_128")

    kwargs: dict = {
        "voice_id": resolved_voice,
        "text": text,
        "model_id": model,
        "output_format": output_format,
    }
    if language_code:
        kwargs["language_code"] = language_code

    loop = asyncio.get_event_loop()
    import queue, threading

    q: queue.Queue = queue.Queue()

    def _stream():
        try:
            for chunk in client.text_to_speech.convert_as_stream(**kwargs):
                if chunk:
                    q.put(chunk)
        finally:
            q.put(None)

    thread = threading.Thread(target=_stream, daemon=True)
    thread.start()

    while True:
        chunk = await loop.run_in_executor(None, q.get)
        if chunk is None:
            break
        yield chunk
