"""Spitch TTS model definitions – 40 African-language voices."""

from typing import Literal

SpitchTTSModel = Literal["legacy"]

SpitchTTSLanguage = Literal["en", "ha", "ig", "yo"]

# Spitch-specific audio formats (superset of common formats)
SpitchResponseFormat = Literal[
    "wav",       # Standard wave (default)
    "mp3",       # MPEG Layer III
    "ogg_opus",  # OGG container with Opus codec
    "webm_opus", # WebM container with Opus codec
    "flac",      # Free Lossless Audio Codec
    "pcm_s16le", # Raw PCM 16-bit little-endian
    "mulaw",     # μ-law encoded audio
    "alaw",      # A-law encoded audio
]

# Languages supported by Spitch TTS
SPITCH_TTS_LANGUAGES: frozenset[str] = frozenset(SpitchTTSLanguage.__args__)  # type: ignore[attr-defined]

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "spitch": frozenset(SpitchTTSModel.__args__),  # type: ignore[attr-defined]
}

# Voice validation is skipped for Spitch – 40 voices exist; see docs.spitch.app/concepts/voices
MODEL_VOICES: dict[str, frozenset[str]] = {}

DEFAULT_VOICE: dict[str, str] = {}
