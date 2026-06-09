"""AI chat endpoints — JWT + RBAC protected, optional session history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.rbac import require_roles
from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.ai import ChatRequest, ChatResponse
from app.services import session as session_service
from app.services.chat import main as chat_service
from app.services.embedding import main as embedding_service
from app.services.vectordb import main as vectordb

router = APIRouter(prefix="/ai", tags=["AI / Chat"])

_cfg = get_config()
_rl = _cfg.get("llm", {}).get("rate_limit", {})


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: dict = Depends(rate_limit(part="chat", user_limit=_rl["user"], admin_limit=_rl["admin"])),
) -> ChatResponse:
    # Build message list: history (if session) + new messages
    new_msgs = [m.model_dump() for m in body.messages]
    if body.session_id:
        history = await session_service.get_history(body.session_id)
        msgs = history + new_msgs
    else:
        msgs = new_msgs

    # RAG context from the first user message
    user_text = body.messages[0].content
    embedding = await embedding_service.get_embedding(text=user_text)
    context = await vectordb.retrieve(
        embedding=embedding,
        collection_name=get_config()["llm"]["vector_database"]["collection_name"],
    )

    reply = await chat_service.chat(
        context=context,
        messages=msgs,
        provider=body.provider,
        model=body.model,  # type: ignore[arg-type]
        system=body.system,
        max_tokens=body.max_tokens,
    )

    # Persist new turn to session history
    if body.session_id:
        await session_service.append(body.session_id, "user", user_text)
        await session_service.append(body.session_id, "assistant", reply)

    return ChatResponse(
        reply=reply,
        provider=body.provider,
        model=body.model,  # type: ignore[arg-type]
        session_id=body.session_id,
    )


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    _user: dict = Depends(require_roles("admin")),
) -> StreamingResponse:
    new_msgs = [m.model_dump() for m in body.messages]
    if body.session_id:
        history = await session_service.get_history(body.session_id)
        msgs = history + new_msgs
    else:
        msgs = new_msgs

    collected: list[str] = []

    async def _generator():
        async for chunk in chat_service.stream_chat(
            messages=msgs,
            provider=body.provider,
            model=body.model,  # type: ignore[arg-type]
            system=body.system,
            max_tokens=body.max_tokens,
        ):
            collected.append(chunk)
            yield chunk

        # Persist after stream completes
        if body.session_id:
            user_text = body.messages[0].content
            await session_service.append(body.session_id, "user", user_text)
            await session_service.append(body.session_id, "assistant", "".join(collected))

    return StreamingResponse(_generator(), media_type="text/plain")


# ── Session management ────────────────────────────────────────────────────────

@router.get(
    "/session/{session_id}",
    summary="Get session history",
    description="Returns stored message history for a session. Admin only.",
)
async def get_session(
    session_id: str,
    _user: dict = Depends(require_roles("admin")),
) -> dict:
    history = await session_service.get_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.delete(
    "/session/{session_id}",
    summary="Clear session history",
    description="Deletes all stored messages for a session.",
)
async def delete_session(
    session_id: str,
    _user: dict = Depends(require_roles("admin")),
) -> dict:
    deleted = await session_service.clear(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or already empty.",
        )
    return {"session_id": session_id, "status": "cleared"}
