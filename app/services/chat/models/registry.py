"""Merged provider → model lookup table for chat request validation."""

from app.services.chat.models import anthropic as _anthropic
from app.services.chat.models import groq as _groq
from app.services.chat.models import openai as _openai

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    **_anthropic.PROVIDER_MODELS,
    **_openai.PROVIDER_MODELS,
    **_groq.PROVIDER_MODELS,
}

DEFAULT_MODEL: dict[str, str] = {
    "anthropic": _anthropic.DEFAULT_MODEL,
    "openai": _openai.DEFAULT_MODEL,
    "groq": _groq.DEFAULT_MODEL,
}
