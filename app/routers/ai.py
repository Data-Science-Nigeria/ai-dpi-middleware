"""AI endpoints — protected by OAuth2 JWT bearer auth."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.oauth import get_current_user
from app.services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["AI"])


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    system: str | None = None
    max_tokens: int = Field(1024, ge=1, le=8096)
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: dict = Depends(get_current_user),
) -> ChatResponse | StreamingResponse:
    msgs = [m.model_dump() for m in body.messages]

    if body.stream:
        async def _generator():
            async for chunk in ai_service.stream_chat(msgs, body.system, body.max_tokens):
                yield chunk

        return StreamingResponse(_generator(), media_type="text/plain")

    reply = await ai_service.chat(msgs, body.system, body.max_tokens)
    return ChatResponse(reply=reply)
