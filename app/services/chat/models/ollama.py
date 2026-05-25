"""Ollama model definitions.

Ollama supports any model the operator has pulled — we cannot enumerate them
statically. We accept any non-empty string as a valid model name so operators
can use whatever they have pulled (llama3.2, mistral, phi3, qwen2.5, etc.).
The sentinel PROVIDER_MODELS value uses a special marker understood by
ChatRequest.resolve_and_validate_model.
"""

DEFAULT_MODEL = "llama3.2"

# None signals "accept any string" — validated in ChatRequest
PROVIDER_MODELS: dict[str, frozenset | None] = {
    "ollama": None,
}
