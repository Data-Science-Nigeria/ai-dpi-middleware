"""TTS endpoints — protected by JWT + RBAC."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.auth.rbac import require_roles
from app.schemas.tts import TTSRequest
from app.services.tts.main import synthesize

router = APIRouter(prefix="/tts", tags=["TTS"])

_MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "opus": "audio/ogg",
    "pcm": "audio/pcm",
}


@router.post("/synthesize")
async def synthesize_endpoint(
    body: TTSRequest,
    _user: dict = Depends(require_roles("user", "admin")),
) -> Response:
    audio_bytes = await synthesize(
        text=body.text,
        voice=body.voice,
        model=body.model,
        response_format=body.response_format,
        provider=body.provider,
    )
    return Response(
        content=audio_bytes,
        media_type=_MEDIA_TYPES.get(body.response_format, "audio/wav"),
    )
