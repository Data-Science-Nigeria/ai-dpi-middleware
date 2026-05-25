from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    text: str = Field(..., description="Source text to extract structured data from.")
    schema: dict[str, Any] = Field(
        ...,
        alias="output_schema",
        description=(
            "JSON Schema (draft-07) describing the structure to extract. "
            "Example: {\"type\": \"object\", \"properties\": {\"name\": {\"type\": \"string\"}}, \"required\": [\"name\"]}"
        ),
    )
    provider: Literal["anthropic", "openai", "groq", "gemini", "ollama"] = Field(
        "anthropic",
        description="LLM provider. Anthropic and OpenAI use native structured output. Others use JSON-mode + schema in prompt.",
    )
    model: str | None = Field(None, description="Model override. Omit for provider default.")
    max_retries: int = Field(1, ge=0, le=3, description="Retries if output fails schema validation.")

    model_config = {"populate_by_name": True}


class ExtractionResponse(BaseModel):
    data: dict[str, Any]
    valid: bool
    errors: list[str] = Field(default_factory=list)
    provider: str
    model: str
