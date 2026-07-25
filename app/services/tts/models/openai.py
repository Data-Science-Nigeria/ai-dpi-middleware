"""OpenAI TTS model definitions."""

from typing import Literal

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

OpenAITTSModel = Literal[
    "tts-1",           # Fast, lower latency
    "tts-1-hd",        # Higher quality
    "gpt-4o-mini-tts", # Latest – supports `instructions` field
]

# ---------------------------------------------------------------------------
# Voices  (shared across all OpenAI TTS models)
# ---------------------------------------------------------------------------

OpenAIVoice = Literal[
    "alloy",
    "ash",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]

# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

OPENAI_MAX_CHARS = 4096

# Only this model supports the `instructions` field
OPENAI_INSTRUCTIONS_MODELS: frozenset[str] = frozenset({"gpt-4o-mini-tts"})

OPENAI_SPEED_MIN = 0.25
OPENAI_SPEED_MAX = 4.0

# ---------------------------------------------------------------------------
# Validation lookup tables
# ---------------------------------------------------------------------------

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "openai": frozenset(OpenAITTSModel.__args__),  # type: ignore[attr-defined]
}

MODEL_VOICES: dict[str, frozenset[str]] = {
    model: frozenset(OpenAIVoice.__args__)          # type: ignore[attr-defined]
    for model in OpenAITTSModel.__args__            # type: ignore[attr-defined]
}

# ---------------------------------------------------------------------------
# Model → default voice
# ---------------------------------------------------------------------------

DEFAULT_VOICE: dict[str, str] = {
    "tts-1": "alloy",
    "tts-1-hd": "alloy",
    "gpt-4o-mini-tts": "alloy",
}
