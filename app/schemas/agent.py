from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    messages: list[AgentMessage] = Field(
        ...,
        description="Conversation messages. Last message is the current user goal/instruction.",
    )
    provider: Literal["anthropic", "openai", "groq", "gemini", "ollama"] = Field(
        "anthropic",
        description="LLM provider. Anthropic and OpenAI/Groq support full tool-calling loop. Gemini/Ollama use single-shot mode.",
    )
    model: str | None = Field(None, description="Model override. Omit for provider default.")
    system: str | None = Field(None, description="System prompt override.")
    max_tokens: int = Field(2048, ge=1, le=8096)
    tools: list[str] | None = Field(
        None,
        description="Restrict agent to specific tools by name. Omit to allow all built-in tools.",
    )


class ToolCall(BaseModel):
    tool: str
    input: dict[str, Any]
    output: str


class AgentResponse(BaseModel):
    reply: str
    provider: str
    model: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    iterations: int
