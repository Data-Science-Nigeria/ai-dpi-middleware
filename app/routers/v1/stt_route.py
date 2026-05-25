"""STT endpoints — protected by JWT + RBAC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.stt import TranscriptionResponse
from app.services import redis as redis_service
from app.services.stt.main import transcribe
from app.services.stt.models.deepgram import DEEPGRAM_LANGUAGES
from app.services.stt.models.intron import INTRON_STT_LANGUAGES
from app.services.stt.models.registry import PROVIDER_MODELS
from app.services.stt.models.spitch import (
    SPITCH_ACCEPTED_EXTENSIONS,
    SPITCH_LANGUAGES,
    SPITCH_TIMESTAMP_MODELS,
)

router = APIRouter(prefix="/stt", tags=["STT"])

_cfg = get_config()
_rl = _cfg.get('stt', {}).get('rate_limit', {})

# Allowed audio extensions for Groq/OpenAI
_GENERAL_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
})

_MAX_FILE_BYTES: int = _cfg.get('speech', {}).get('max_file_size_mb', 50) * 1024 * 1024
_SPITCH_MAX_FILE_BYTES: int = _cfg.get('speech', {}).get('spitch_max_file_size_mb', 25) * 1024 * 1024

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
_CACHE_TTL = _cfg.get('stt', {}).get('session_ttl_hours', 24) * 3600


def _cache_key(
    file_bytes: bytes,
    provider: str,
    model: str,
    language: str | None,
    prompt: str | None,
    special_words: str | None,
    timestamp: str,
) -> str:
    digest = hashlib.sha256(file_bytes).hexdigest()
    extras = hashlib.sha256(f"{special_words or ''}:{timestamp}".encode()).hexdigest()[:8]
    return f"{_CACHE_PREFIX}{digest}:{provider}:{model}:{language or ''}:{hashlib.sha256((prompt or '').encode()).hexdigest()[:8]}:{extras}"


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
| `spitch` | `legacy` | African-language support *(default)* |
| `spitch` | `mansa_v1` | Enhanced accuracy for African-accented English; supports timestamps |

**Accepted formats**
- Groq / OpenAI: `.mp3` `.wav` `.flac` `.aac` `.ogg` `.wma` `.m4a` (50 MB limit)
- Spitch: `.mp3` `.wav` `.m4a` `.ogg` (25 MB limit)

**Spitch languages:** `en`, `yo`, `ha`, `ig`, `am`

**Spitch-only fields**
- `language` — **required** for Spitch (`en`, `yo`, `ha`, `ig`, `am`)
- `special_words` — custom vocabulary hint to improve recognition
- `timestamp` — `none` | `sentence` | `word` (only with `mansa_v1`)
""",
    responses={
        200: {"description": "Transcription result"},
        400: {"description": "Invalid file type, file too large, or missing required field"},
        422: {"description": "Unsupported provider or model"},
    },
)
async def transcribe_endpoint(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    provider: Literal["groq", "openai", "spitch", "deepgram", "intron"] = Form("groq"),
    model: str | None = Form(None, description="STT model. Defaults to the provider's recommended model."),
    language: str | None = Form(None, description="Language code. Required for Spitch and Intron. Auto-detected for Groq/OpenAI/Deepgram."),
    prompt: str | None = Form(None, description="Context hint to improve accuracy (Groq/OpenAI only)."),
    special_words: str | None = Form(None, description="Custom vocabulary hint (Spitch/Intron only)."),
    timestamp: Literal["none", "sentence", "word"] = Form("none", description="Timestamp granularity. Spitch mansa_v1 and Intron only."),
    _user: dict = Depends(rate_limit(part = "stt", user_limit=_rl['user'], admin_limit=_rl['admin'])),
) -> TranscriptionResponse:

    # --- Resolve default model per provider ---
    _defaults = {
        "groq": "whisper-large-v3-turbo",
        "openai": "gpt-4o-mini-transcribe",
        "spitch": "legacy",
        "deepgram": "nova-3",
        "intron": "sahara-v1",
    }
    resolved_model = model or _defaults[provider]

    # --- Validate provider → model ---
    supported = PROVIDER_MODELS.get(provider, frozenset())
    if resolved_model not in supported:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Provider '{provider}' does not support model '{resolved_model}'. Supported: {sorted(supported)}.",
        )

    # --- Provider-specific language validation ---
    if provider == "spitch":
        if not language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Spitch requires a `language`. Supported: {sorted(SPITCH_LANGUAGES)}.",
            )
        if language not in SPITCH_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{language}' is not supported by Spitch. Supported: {sorted(SPITCH_LANGUAGES)}.",
            )
        if timestamp != "none" and resolved_model not in SPITCH_TIMESTAMP_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timestamps are only supported by: {sorted(SPITCH_TIMESTAMP_MODELS)}.",
            )

    if provider == "intron":
        if not language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Intron requires a `language`. Supported: {sorted(INTRON_STT_LANGUAGES)}.",
            )
        if language not in INTRON_STT_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{language}' is not supported by Intron. Supported: {sorted(INTRON_STT_LANGUAGES)}.",
            )

    if provider == "deepgram" and language and language not in DEEPGRAM_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{language}' is not supported by Deepgram. Supported: {sorted(DEEPGRAM_LANGUAGES)}.",
        )

    # --- Validate file extension ---
    ext = Path(file.filename or "").suffix.lower()
    _small_providers = {"spitch", "intron"}
    allowed_exts = SPITCH_ACCEPTED_EXTENSIONS if provider in _small_providers else _GENERAL_AUDIO_EXTENSIONS
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed for provider '{provider}'. Accepted: {sorted(allowed_exts)}.",
        )

    # --- Validate file size ---
    file_bytes = await file.read()
    max_bytes = _SPITCH_MAX_FILE_BYTES if provider in _small_providers else _MAX_FILE_BYTES
    max_mb = _cfg.get('speech', {}).get('spitch_max_file_size_mb', 25) if provider in _small_providers else _cfg.get('speech', {}).get('max_file_size_mb', 50)
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds the {max_mb} MB limit ({len(file_bytes) / 1024 / 1024:.1f} MB received).",
        )

    content_type = _MIME_TYPES.get(ext, file.content_type or "application/octet-stream")

    # --- Cache lookup ---
    redis = redis_service.get_client()
    key = _cache_key(file_bytes, provider, resolved_model, language, prompt, special_words, timestamp)
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
        special_words=special_words,
        timestamp=timestamp,
    )

    response = TranscriptionResponse(
        text=result["text"],
        language=result.get("language"),
        duration=result.get("duration"),
        provider=provider,
        model=resolved_model,
    )

    await redis.setex(key, _CACHE_TTL, json.dumps(response.model_dump()))
    return response
