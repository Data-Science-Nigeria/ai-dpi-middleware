"""AI chat endpoints — protected by JWT + RBAC."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.rbac import require_roles
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.chat import main as chat_service

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: dict = Depends(require_roles("user", "admin")),
) -> ChatResponse:
    msgs = [m.model_dump() for m in body.messages]
    reply = await chat_service.chat(
        messages=msgs,
        provider=body.provider,
        model=body.model, # type: ignore
        system=body.system,
        max_tokens=body.max_tokens,
    )
    return ChatResponse(reply=reply, provider=body.provider, model=body.model) # type: ignore


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    _user: dict = Depends(require_roles("admin")),
) -> StreamingResponse:
    msgs = [m.model_dump() for m in body.messages]

    async def _generator():
        async for chunk in chat_service.stream_chat(
            messages=msgs,
            provider=body.provider,
            model=body.model, # type: ignore
            system=body.system,
            max_tokens=body.max_tokens,
        ):
            yield chunk

    return StreamingResponse(_generator(), media_type="text/plain")
