"""AI chat endpoints — protected by JWT + RBAC."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.rbac import require_roles
from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.chat import main as chat_service
from app.services.embedding import main as embedding_service
from app.services.vectordb import main as vectordb

router = APIRouter(prefix="/ai", tags=["AI"])

_cfg = get_config()
_rl = _cfg.get('llm', {}).get('rate_limit', {})

@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: dict = Depends(rate_limit(part = "chat", user_limit=_rl['user'], admin_limit=_rl['admin'])),
) -> ChatResponse:
    msgs = [m.model_dump() for m in body.messages]

    embedding = await embedding_service.get_embedding(text=body.messages[0].content, model=body.model)
    context = await vectordb.retrieve(embedding=embedding, collection_name=get_config()["llm"]["vector_database"]['collection_name'])

    reply = await chat_service.chat(
        context= context,
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
