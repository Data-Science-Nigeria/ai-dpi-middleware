"""Groq chat model definitions — fast open-source LLM inference."""

from typing import Literal

GroqChatModel = Literal[
    "llama-3.3-70b-versatile",                       # Best all-round Llama 3.3
    "llama-3.1-8b-instant",                          # Fastest, lowest latency
    "meta-llama/llama-4-scout-17b-16e-instruct",     # Llama 4 Scout
    "meta-llama/llama-4-maverick-17b-128e-instruct", # Llama 4 Maverick
    "mixtral-8x7b-32768",                            # Mixtral MoE, 32K context
    "gemma2-9b-it",                                  # Google Gemma 2
]

GROQ_MAX_TOKENS_MAX = 8192

DEFAULT_MODEL = "llama-3.3-70b-versatile"

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "groq": frozenset(GroqChatModel.__args__),  # type: ignore[attr-defined]
}
