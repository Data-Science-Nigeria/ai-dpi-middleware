"""Groq chat model definitions — fast open-source LLM inference."""

from typing import Literal

GroqChatModel = Literal[
    # Llama 4 (preview)
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    # Llama 3.x (production)
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    # Groq compound models
    "groq/compound",
    "groq/compound-mini",
    # Other open models on Groq
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "qwen/qwen3-32b",
]

GROQ_MAX_TOKENS_MAX = 8192

DEFAULT_MODEL = "llama-3.3-70b-versatile"

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "groq": frozenset(GroqChatModel.__args__),  # type: ignore[attr-defined]
}
