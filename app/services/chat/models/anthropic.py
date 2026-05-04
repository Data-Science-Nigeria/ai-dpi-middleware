"""Anthropic chat model definitions."""

from typing import Literal

AnthropicChatModel = Literal[
    "claude-opus-4-7",           # Most capable
    "claude-sonnet-4-6",         # Balanced speed and capability
    "claude-haiku-4-5-20251001", # Fastest, most compact
]

ANTHROPIC_MAX_TOKENS_MAX = 8096

DEFAULT_MODEL = "claude-sonnet-4-6"

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "anthropic": frozenset(AnthropicChatModel.__args__),  # type: ignore[attr-defined]
}
