"""OpenAI chat model definitions."""

from typing import Literal

OpenAIChatModel = Literal[
    "gpt-4o",       # Flagship multimodal model
    "gpt-4o-mini",  # Fast and affordable
    "o1",           # Reasoning model
    "o3-mini",      # Compact reasoning model
]

# Reasoning models do not support system messages or streaming
OPENAI_REASONING_MODELS: frozenset[str] = frozenset({"o1", "o3-mini"})

OPENAI_MAX_TOKENS_MAX = 16384

DEFAULT_MODEL = "gpt-4o"

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "openai": frozenset(OpenAIChatModel.__args__),  # type: ignore[attr-defined]
}
