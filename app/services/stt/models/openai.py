"""OpenAI STT model definitions."""

from typing import Literal

OpenAISTTModel = Literal[
    "whisper-1",               # Classic, battle-tested
    "gpt-4o-transcribe",       # Higher accuracy
    "gpt-4o-mini-transcribe",  # Fast + affordable
]

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "openai": frozenset(OpenAISTTModel.__args__),  # type: ignore[attr-defined]
}

DEFAULT_MODEL = "gpt-4o-mini-transcribe"
