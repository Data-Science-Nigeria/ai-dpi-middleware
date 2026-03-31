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


@router.post(
    "/synthesize",
    summary="Synthesize speech from text",
    description="""
Convert text to speech using the specified provider, model, and voice.

**Providers & models**

| Provider | Model | Language | Vocal directions |
|----------|-------|----------|-----------------|
| `groq` | `playai-tts` | English | No |
| `groq` | `playai-tts-arabic` | Arabic | No |
| `groq` | `canopylabs/orpheus-v1-english` | English | Yes |
| `groq` | `canopylabs/orpheus-arabic-saudi` | Arabic (Saudi) | No |

**Orpheus limits**
- Input is capped at **200 characters** for all `canopylabs/*` models.
- The English model (`canopylabs/orpheus-v1-english`) supports inline **vocal-direction tags**
  embedded directly in the text, e.g.:
  `"Good morning! [cheerful] Welcome to the service."`
  Available tags: `[cheerful]`, `[sad]`, `[angry]`, `[fearful]`, `[disgusted]`, `[surprised]`,
  `[friendly]`, `[casual]`, `[authoritatively]`, `[formally]`, `[whisper]`, `[gravelly whisper]`,
  `[rapid babbling]`, `[laughing]`, `[giggling]`, `[sighing]`, `[crying]`, `[screaming]`.

**Voices**

| Model | Voices |
|-------|--------|
| `playai-tts` / `playai-tts-arabic` | Aaliyah, Adelaide, Angelo, Arsenio, Barbra, Briggs, Calum, Celeste, Chandra, Chip, Cillian, Deedee, Dexter, Edmund, Evangeline, Felicity, Gideon, Hank, Hera, Jedidiah, Kendrick, Kitty, Quinn, Tara, Thunder |
| `canopylabs/orpheus-v1-english` | Autumn, Diana, Hannah *(f)* · Austin, Daniel, Troy *(m)* |
| `canopylabs/orpheus-arabic-saudi` | Lulwa, Noura *(f)* · Fahad, Sultan *(m)* |

Omit `voice` to use the model's default.

**Response**
Raw audio bytes with the appropriate `Content-Type` header (`audio/wav` by default).
""",
    response_class=Response,
    responses={
        200: {"content": {"audio/wav": {}, "audio/mpeg": {}, "audio/flac": {}, "audio/aac": {}, "audio/ogg": {}, "audio/pcm": {}}, "description": "Audio file"},
        422: {"description": "Validation error — invalid provider/model/voice combination or text too long"},
    },
)
async def synthesize_endpoint(
    body: TTSRequest,
    _user: dict = Depends(require_roles("user", "admin")),
) -> Response:
    try:
        audio_bytes = await synthesize(
            text=body.text,
            voice=body.voice,
            model=body.model,
            response_format=body.response_format,
            provider=body.provider,
            speed=body.speed,
            instructions=body.instructions,
        )
        media_type = _MEDIA_TYPES.get(body.response_format, "audio/wav")
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{body.response_format}"',
                "Content-Length": str(len(audio_bytes)),
            },
        )
    except ValueError as e:
        return Response(content=str(e), status_code=422)