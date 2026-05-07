from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.chat.models.registry import DEFAULT_MODEL, PROVIDER_MODELS


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    provider: Literal["anthropic", "openai", "groq"] = Field(
        "anthropic",
        description="LLM provider to use.",
    )
    model: str | None = Field(
        None,
        description=(
            "Chat model. Omit to use the provider default. "
            "Anthropic: claude-opus-4-7, claude-sonnet-4-6 (default), claude-haiku-4-5-20251001. "
            "OpenAI: gpt-4o (default), gpt-4o-mini, o1, o3-mini. "
            "Groq: llama-3.3-70b-versatile (default), llama-3.1-8b-instant, "
            "meta-llama/llama-4-scout-17b-16e-instruct, meta-llama/llama-4-maverick-17b-128e-instruct, "
            "mixtral-8x7b-32768, gemma2-9b-it."
        ),
    )
    system: str | None = None
    max_tokens: int = Field(1024, ge=1, le=8096)

    @model_validator(mode="after")
    def resolve_and_validate_model(self) -> ChatRequest:
        if self.model is None:
            self.model = DEFAULT_MODEL.get(self.provider)

        supported = PROVIDER_MODELS.get(self.provider, frozenset())
        if self.model not in supported:
            raise ValueError(
                f"Provider '{self.provider}' does not support model '{self.model}'. "
                f"Supported models: {sorted(supported)}."
            )
        return self


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str

class EmbeddingResponse(BaseModel):
    status: bool = True
    message: str = "Creating status successfully"


class EmbeddingRequest(BaseModel):
    text: str
    model: str
    collection_name: str | None = None