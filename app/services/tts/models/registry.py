"""Merged provider/model/voice lookup tables used for request validation."""

from app.services.tts.models import groq as _groq
from app.services.tts.models import openai as _openai
from app.services.tts.models import spitch as _spitch

# provider → frozenset of supported model IDs
PROVIDER_MODELS: dict[str, frozenset[str]] = {
    **_groq.PROVIDER_MODELS,
    **_openai.PROVIDER_MODELS,
    **_spitch.PROVIDER_MODELS,
}

# model → frozenset of valid voice IDs (None/missing entry = skip validation)
MODEL_VOICES: dict[str, frozenset[str]] = {
    **_groq.MODEL_VOICES,
    **_openai.MODEL_VOICES,
    **_spitch.MODEL_VOICES,
}

# model → default voice
DEFAULT_VOICE: dict[str, str] = {
    **_groq.DEFAULT_VOICE,
    **_openai.DEFAULT_VOICE,
    **_spitch.DEFAULT_VOICE,
}
