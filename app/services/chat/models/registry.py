"""Merged provider → model lookup table for chat request validation."""

from app.services.chat.models import anthropic as _anthropic
from app.services.chat.models import gemini as _gemini
from app.services.chat.models import groq as _groq
from app.services.chat.models import ollama as _ollama
from app.services.chat.models import openai as _openai

# None values mean "accept any model string" (open-ended providers like Ollama)
PROVIDER_MODELS: dict[str, frozenset[str] | None] = {
    **_anthropic.PROVIDER_MODELS,
    **_openai.PROVIDER_MODELS,
    **_groq.PROVIDER_MODELS,
    **_gemini.PROVIDER_MODELS,
    **_ollama.PROVIDER_MODELS,
}

DEFAULT_MODEL: dict[str, str] = {
    "anthropic": _anthropic.DEFAULT_MODEL,
    "openai": _openai.DEFAULT_MODEL,
    "groq": _groq.DEFAULT_MODEL,
    "gemini": _gemini.DEFAULT_MODEL,
    "ollama": _ollama.DEFAULT_MODEL,
}
