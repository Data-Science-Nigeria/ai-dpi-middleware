from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.chat.models.registry import DEFAULT_MODEL, PROVIDER_MODELS


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    session_id: str | None = Field(
        None,
        description=(
            "Optional session ID for multi-turn conversation history. "
            "When provided and Redis is enabled, prior turns are prepended automatically. "
            "Any non-empty string is valid — use a UUID or a user/thread identifier."
        ),
    )
    messages: list[Message] = Field(..., min_length=1)
    provider: Literal["anthropic", "openai", "groq", "gemini", "ollama"] = Field(
        "anthropic",
        description="LLM provider to use. Use 'ollama' for sovereign/local inference.",
    )
    model: str | None = Field(
        None,
        description=(
            "Chat model. Omit to use the provider default. "
            "Anthropic: claude-opus-4-7, claude-sonnet-4-6 (default), claude-haiku-4-5-20251001. "
            "OpenAI: gpt-5, gpt-5-mini, gpt-4o (default), gpt-4o-mini, o1, o3, o3-mini, o4-mini. "
            "Groq: llama-3.3-70b-versatile (default), llama-3.1-8b-instant, "
            "meta-llama/llama-4-scout-17b-16e-instruct, meta-llama/llama-4-maverick-17b-128e-instruct, "
            "groq/compound, groq/compound-mini, mixtral-8x7b-32768, gemma2-9b-it, qwen/qwen3-32b. "
            "Gemini: gemini-2.5-pro, gemini-2.5-flash (default), gemini-2.5-flash-lite, "
            "gemini-2.0-flash, gemini-2.0-flash-lite, gemini-1.5-pro, gemini-1.5-flash. "
            "Ollama: any model you have pulled locally, e.g. llama3.2 (default), mistral, phi3."
        ),
    )
    system: str | None = None
    max_tokens: int = Field(1024, ge=1, le=8096)

    @model_validator(mode="after")
    def resolve_and_validate_model(self) -> "ChatRequest":
        if self.model is None:
            self.model = DEFAULT_MODEL.get(self.provider)

        supported = PROVIDER_MODELS.get(self.provider)
        # None means the provider accepts any model string (e.g. Ollama)
        if supported is not None and self.model not in supported:
            raise ValueError(
                f"Provider '{self.provider}' does not support model '{self.model}'. "
                f"Supported models: {sorted(supported)}."
            )
        return self


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    session_id: str | None = None

class EmbeddingResponse(BaseModel):
    status: bool = True
    message: str = "Creating status successfully"


class EmbeddingRequest(BaseModel):
    text: str
    model: str | None = Field(None, description="Embedding model. Omit to use the provider default from config.")
    collection_name: str | None = None