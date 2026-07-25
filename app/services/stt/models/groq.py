"""Groq STT model definitions – Whisper via Groq inference."""

from typing import Literal

GroqSTTModel = Literal[
    "whisper-large-v3",          # Most accurate
    "whisper-large-v3-turbo",    # Fast + accurate
    "distil-whisper-large-v2",   # Fastest
]

# Models that support per-word timestamps in verbose_json
GROQ_WORD_TIMESTAMPS_MODELS: frozenset[str] = frozenset({
    "whisper-large-v3",
    "whisper-large-v3-turbo",
})

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "groq": frozenset(GroqSTTModel.__args__),  # type: ignore[attr-defined]
}

DEFAULT_MODEL = "whisper-large-v3-turbo"
