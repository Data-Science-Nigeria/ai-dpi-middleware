"""TTS endpoints — protected by JWT + RBAC."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.tts import TTSRequest
from app.services import redis as redis_service
from app.services.tts.main import synthesize, stream_synthesize

router = APIRouter(prefix="/tts", tags=["TTS"])
_cfg = get_config()
_rl = _cfg.get('tts', {}).get('rate_limit', {})

_DEFAULT_MEDIA_TYPE = "audio/wav"
_MEDIA_TYPES = {
    "wav":       _DEFAULT_MEDIA_TYPE,
    "mp3":       "audio/mpeg",
    "flac":      "audio/flac",
    "aac":       "audio/aac",
    "opus":      "audio/ogg",
    "pcm":       "audio/pcm",
    "ogg_opus":  "audio/ogg",
    "webm_opus": "audio/webm",
    "pcm_s16le": "audio/pcm",
    "mulaw":     "audio/basic",
    "ulaw":      "audio/basic",
    "alaw":      "audio/alaw",
}

_CACHE_PREFIX = "tts:cache:"
_CACHE_TTL = get_config().get('tts', {}).get('session_ttl_hours', 24) * 3600


def _cache_key(body: TTSRequest) -> str:
    text_hash = hashlib.sha256(body.text.encode()).hexdigest()
    instructions_hash = hashlib.sha256((body.instructions or "").encode()).hexdigest()[:8]
    return (
        f"{_CACHE_PREFIX}{text_hash}"
        f":{body.provider}:{body.model}:{body.voice or ''}:{body.response_format}"
        f":{body.speed}:{instructions_hash}:{body.language or ''}"
    )


@router.post(
    "/synthesize",
    summary="Synthesize speech from text",
    description="""
Convert text to speech. Five providers, true global multilingual coverage.

**Providers & models**

| Provider | Model | Languages | Notes |
|----------|-------|-----------|-------|
| `groq` | `playai-tts` | English | — |
| `groq` | `playai-tts-arabic` | Arabic | — |
| `groq` | `canopylabs/orpheus-v1-english` | English | Vocal direction tags |
| `groq` | `canopylabs/orpheus-arabic-saudi` | Arabic (Saudi) | — |
| `openai` | `tts-1` | Multilingual | Fast |
| `openai` | `tts-1-hd` | Multilingual | High quality |
| `openai` | `gpt-4o-mini-tts` | Multilingual | Supports `instructions` |
| `elevenlabs` | `eleven_multilingual_v2` | 32 languages | Best quality *(default)* |
| `elevenlabs` | `eleven_flash_v2_5` | 32 languages | Ultra-low latency |
| `elevenlabs` | `eleven_turbo_v2_5` | 32 languages | Low latency |
| `elevenlabs` | `eleven_monolingual_v1` | English only | Legacy |
| `spitch` | `legacy` | en, ha, ig, yo | West African |
| `intron` | `sahara-tts-v1` | sw, ha, yo, ig, am, en | Sahara African |

**ElevenLabs languages** (32): en, ja, zh, de, hi, fr, ko, pt, it, es, id, nl, tr, fil, pl, sv, bg, ro, ar, cs, el, fi, hr, ms, sk, da, ta, uk, ru, hu, no, vi

**Orpheus vocal-direction tags** (canopylabs/orpheus-v1-english only):
`[cheerful]` `[sad]` `[angry]` `[whisper]` `[laughing]` `[formal]` and more. Input capped at 200 chars.

**Response**
Raw audio bytes with the appropriate `Content-Type` header.
""",
    response_class=Response,
    responses={
        200: {"content": {_DEFAULT_MEDIA_TYPE: {}, "audio/mpeg": {}, "audio/flac": {}, "audio/aac": {}, "audio/ogg": {}, "audio/pcm": {}}, "description": "Audio file"},
        422: {"description": "Validation error — invalid provider/model/voice combination or text too long"},
    },
)
async def synthesize_endpoint(
    body: TTSRequest,
    _user: Annotated[dict, Depends(rate_limit(part = "tts", user_limit=_rl['user'], admin_limit=_rl['admin']))],
) -> Response:
    media_type = _MEDIA_TYPES.get(body.response_format, _DEFAULT_MEDIA_TYPE)

    redis = redis_service.get_client()
    key = _cache_key(body)
    cached = await redis.get(key)
    if cached:
        return Response(
            content=cached,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{body.response_format}"',
                "Content-Length": str(len(cached)),
                "X-Cache": "HIT",
            },
        )

    try:
        audio_bytes = await synthesize(
            text=body.text,
            voice=body.voice,
            model=body.model,
            response_format=body.response_format,
            provider=body.provider,
            speed=body.speed,
            instructions=body.instructions,
            language=body.language,
        )
    except ValueError as e:
        return Response(content=str(e), status_code=422)

    await redis.setex(key, _CACHE_TTL, audio_bytes)

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="speech.{body.response_format}"',
            "Content-Length": str(len(audio_bytes)),
            "X-Cache": "MISS",
        },
    )


@router.post(
    "/stream",
    summary="Stream speech synthesis (chunked audio)",
    description="""
Stream text-to-speech audio as it is generated — lower time-to-first-byte than `/synthesize`.

**Supported providers:** `openai`, `groq`, `elevenlabs`

Spitch and Intron do not expose streaming APIs — use `/synthesize` for those.

Response is a chunked `audio/*` stream. Suitable for voice agents and real-time playback.
Not cached (streaming responses are not stored in Redis).
""",
    response_class=StreamingResponse,
    responses={
        200: {"content": {_DEFAULT_MEDIA_TYPE: {}, "audio/mpeg": {}}, "description": "Chunked audio stream"},
    },
)
async def stream_endpoint(
    body: TTSRequest,
    _user: Annotated[dict, Depends(rate_limit(part="tts", user_limit=_rl['user'], admin_limit=_rl['admin']))],
) -> StreamingResponse:
    media_type = _MEDIA_TYPES.get(body.response_format, _DEFAULT_MEDIA_TYPE)
    try:
        audio_iter = stream_synthesize(
            text=body.text,
            voice=body.voice,
            model=body.model,
            response_format=body.response_format,
            provider=body.provider,
            speed=body.speed,
            instructions=body.instructions,
            language=body.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return StreamingResponse(
        audio_iter,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="speech.{body.response_format}"'},
    )