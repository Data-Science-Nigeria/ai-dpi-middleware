"""Merged provider → model lookup table for STT request validation."""

from app.services.stt.models import groq as _groq
from app.services.stt.models import openai as _openai
from app.services.stt.models import spitch as _spitch

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    **_groq.PROVIDER_MODELS,
    **_openai.PROVIDER_MODELS,
    **_spitch.PROVIDER_MODELS,
}
