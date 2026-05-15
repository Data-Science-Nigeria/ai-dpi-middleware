from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.chat.models.registry import DEFAULT_MODEL, PROVIDER_MODELS

_SUPPORTED_PROVIDERS = frozenset(PROVIDER_MODELS.keys())


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to translate.")
    source_language: str | None = Field(
        None,
        description="BCP-47 source language code (e.g. 'en', 'fr', 'yo'). Omit for auto-detection.",
    )
    target_language: str = Field(
        ...,
        description="BCP-47 target language code (e.g. 'sw', 'ha', 'fr', 'ar').",
    )
    provider: Literal["anthropic", "openai", "groq", "gemini"] = Field(
        "anthropic",
        description="LLM provider to use for translation.",
    )
    model: str | None = Field(
        None,
        description="Model to use. Omit to use the provider default.",
    )
    max_tokens: int = Field(4096, ge=1, le=8096)


class TranslateResponse(BaseModel):
    translation: str
    source_language: str | None
    target_language: str
    provider: str
    model: str
