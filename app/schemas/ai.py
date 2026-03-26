from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    system: str | None = None
    max_tokens: int = Field(1024, ge=1, le=8096)


class ChatResponse(BaseModel):
    reply: str
