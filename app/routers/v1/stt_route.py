"""STT endpoints — protected by JWT + RBAC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config_yaml import get_yaml_config
from app.middleware.rate_limit import stt_rate_limit
from app.schemas.stt import TranscriptionResponse
from app.services import redis as redis_service
from app.services.stt.main import transcribe
from app.services.stt.models.registry import PROVIDER_MODELS

router = APIRouter(prefix="/stt", tags=["STT"])

_cfg = get_yaml_config()
_rl = _cfg.security.rate_limits

# Allowed audio extensions (subset of YAML security.upload.allowed_extensions)
_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    ext for ext in _cfg.security.upload.allowed_extensions
    if ext in {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"}
)

# File-size cap (bytes) from YAML speech config
_MAX_FILE_BYTES: int = _cfg.speech.max_file_size_mb * 1024 * 1024

_MIME_TYPES: dict[str, str] = {
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".flac": "audio/flac",
    ".aac":  "audio/aac",
    ".ogg":  "audio/ogg",
    ".wma":  "audio/x-ms-wma",
    ".m4a":  "audio/mp4",
}

_CACHE_PREFIX = "stt:cache:"
_CACHE_TTL = _cfg.chat.session_ttl_hours * 3600


def _cache_key(file_bytes: bytes, provider: str, model: str, language: str | None, prompt: str | None) -> str:
    digest = hashlib.sha256(file_bytes).hexdigest()
    return f"{_CACHE_PREFIX}{digest}:{provider}:{model}:{language or ''}:{hashlib.sha256((prompt or '').encode()).hexdigest()[:8]}"


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe speech from an audio file",
    description="""
Convert an audio file to text using the specified provider and model.

**Providers & models**

| Provider | Model | Notes |
|----------|-------|-------|
| `groq` | `whisper-large-v3` | Most accurate |
| `groq` | `whisper-large-v3-turbo` | Fast + accurate *(default)* |
| `groq` | `distil-whisper-large-v2` | Fastest |
| `openai` | `whisper-1` | Classic |
| `openai` | `gpt-4o-transcribe` | Higher accuracy |
| `openai` | `gpt-4o-mini-transcribe` | Fast + affordable *(default)* |

**Accepted formats:** `.mp3` `.wav` `.flac` `.aac` `.ogg` `.wma` `.m4a`

**File size limit:** 50 MB

**Optional fields**
- `language` — ISO-639-1 code (e.g. `en`, `fr`). Auto-detected when omitted.
- `prompt` — short context hint to improve accuracy (e.g. technical terms, speaker name).
""",
    responses={
        200: {"description": "Transcription result"},
        400: {"description": "Invalid file type or file too large"},
        422: {"description": "Unsupported provider or model"},
    },
)
async def transcribe_endpoint(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    provider: Literal["groq", "openai"] = Form("groq"),
    model: str | None = Form(None, description="STT model. Defaults to the provider's recommended model."),
    language: str | None = Form(None, description="ISO-639-1 language code. Auto-detected if omitted."),
    prompt: str | None = Form(None, description="Optional context hint to improve accuracy."),
    _user: dict = Depends(stt_rate_limit(user_limit=_rl.stt_user, admin_limit=_rl.stt_admin)),
) -> TranscriptionResponse:

    # Validate provider → model
    supported = PROVIDER_MODELS.get(provider, frozenset())
    resolved_model = model or (
        "whisper-large-v3-turbo" if provider == "groq" else "gpt-4o-mini-transcribe"
    )
    if resolved_model not in supported:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Provider '{provider}' does not support model '{resolved_model}'. "
                f"Supported: {sorted(supported)}."
            ),
        )

    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed. Accepted: {sorted(_AUDIO_EXTENSIONS)}.",
        )

    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File exceeds the {_cfg.speech.max_file_size_mb} MB limit "
                f"({len(file_bytes) / 1024 / 1024:.1f} MB received)."
            ),
        )

    content_type = _MIME_TYPES.get(ext, file.content_type or "application/octet-stream")

    # Check cache before calling the provider
    redis = redis_service.get_client()
    key = _cache_key(file_bytes, provider, resolved_model, language, prompt)
    cached = await redis.get(key)
    if cached:
        return TranscriptionResponse(**json.loads(cached))

    result = await transcribe(
        file_bytes=file_bytes,
        filename=file.filename or f"audio{ext}",
        content_type=content_type,
        provider=provider,
        model=resolved_model,
        language=language,
        prompt=prompt,
    )

    response = TranscriptionResponse(
        text=result["text"],
        language=result.get("language"),
        duration=result.get("duration"),
        provider=provider,
        model=resolved_model,
    )

    # Store in cache
    await redis.setex(key, _CACHE_TTL, json.dumps(response.model_dump()))

    return response
