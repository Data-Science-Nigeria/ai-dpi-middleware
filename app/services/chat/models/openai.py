"""OpenAI chat model definitions."""

from typing import Literal

OpenAIChatModel = Literal[
    # GPT-5 family
    "gpt-5",
    "gpt-5-mini",
    # GPT-4o family
    "gpt-4o",
    "gpt-4o-mini",
    # Reasoning models
    "o1",
    "o1-mini",
    "o3",
    "o3-mini",
    "o4-mini",
]

# Reasoning models do not support system messages or streaming
OPENAI_REASONING_MODELS: frozenset[str] = frozenset({"o1", "o1-mini", "o3", "o3-mini", "o4-mini"})

OPENAI_MAX_TOKENS_MAX = 16384

DEFAULT_MODEL = "gpt-4o"

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "openai": frozenset(OpenAIChatModel.__args__),  # type: ignore[attr-defined]
}
