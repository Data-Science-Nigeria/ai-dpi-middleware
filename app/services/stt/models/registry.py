"""Merged provider → model lookup table for STT request validation."""

from app.services.stt.models import groq as _groq
from app.services.stt.models import openai as _openai

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    **_groq.PROVIDER_MODELS,
    **_openai.PROVIDER_MODELS,
}
