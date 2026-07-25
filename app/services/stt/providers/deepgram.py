"""STT provider – Deepgram.

Uses the Deepgram v7 SDK pre-recorded transcription API.
nova-3 supports 100+ languages with automatic language detection.
"""

from __future__ import annotations

from app.providers.deepgram import get_client
from app.services.stt.models.deepgram import DEFAULT_MODEL


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
    prompt: str | None = None,
) -> dict:
    """Transcribe audio using Deepgram's pre-recorded API (v7 SDK).

    Args:
        file_bytes:   Raw audio bytes.
        filename:     Original filename (for logging only).
        content_type: MIME type of the audio file.
        model:        Deepgram model: nova-3, nova-2, enhanced, base.
        language:     BCP-47 code. Pass None to enable auto-detection.
        prompt:       Not used by Deepgram; accepted for interface parity.
    """
    client = get_client()

    kwargs: dict = {
        "request": file_bytes,
        "model": model,
        "smart_format": True,
        "punctuate": True,
    }
    if language:
        kwargs["language"] = language
        kwargs["detect_language"] = False
    else:
        kwargs["detect_language"] = True

    response = await client.listen.v("1").transcribe_file(**kwargs)

    channel = response.results.channels[0]
    alternative = channel.alternatives[0]
    detected = getattr(channel, "detected_language", None) or language

    return {
        "text": alternative.transcript,
        "language": detected,
        "duration": getattr(response.metadata, "duration", None),
    }
