"""AI chat endpoints — protected by JWT + RBAC."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.rbac import require_roles
from app.config import get_config
from app.schemas.ai import EmbeddingRequest, EmbeddingResponse
from app.services.embedding import main as embedding_service
from app.services.vectordb import main as vectordb

router = APIRouter(prefix="/ai", tags=["RAG / Embeddings"])

_cfg = get_config().get('llm', {})

@router.post("/add_vector_db", response_model=EmbeddingResponse)
async def embed_store_text(
    body: EmbeddingRequest,
    _user: dict = Depends(require_roles("admin")),
):
    collection_name = body.collection_name or _cfg["vector_database"]["collection_name"]

    embedding = await embedding_service.get_embedding(text=body.text, model=body.model)

    await vectordb.add(
        collection_name=collection_name,
        embeddings=[embedding],
        documents=[body.text],
    )

    return EmbeddingResponse(status=True, message="Embedding stored successfully")