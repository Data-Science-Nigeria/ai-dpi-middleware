"""Vector DB provider – Pinecone (managed/serverless).

Uses the Pinecone Python SDK v5+. Requires a pre-created index; the index
must have a dimension matching the embedding model output.
"""

from __future__ import annotations

import uuid

from pinecone import Pinecone

from app.config import get_config

_client: Pinecone | None = None


def get_client() -> Pinecone:
    global _client
    if _client is None:
        cfg = get_config()["llm"]["vector_database"]
        _client = Pinecone(api_key=cfg["API_KEY"])
    return _client


async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
) -> None:
    if len(embeddings) != len(documents):
        raise ValueError("embeddings and documents must have the same length")

    client = get_client()
    index = client.Index(collection_name)

    vectors = []
    for i, (doc, emb) in enumerate(zip(documents, embeddings)):
        meta = dict(meta_data[i]) if meta_data and i < len(meta_data) else {}
        meta["text"] = doc
        vectors.append({"id": str(uuid.uuid4()), "values": emb, "metadata": meta})

    index.upsert(vectors=vectors)


async def retrieve(
    embedding: list[float],
    collection_name: str,
    n_results: int | None = None,
) -> str:
    cfg = get_config()["llm"]["vector_database"]
    n = n_results or cfg.get("N_RESULT", 2)

    client = get_client()
    index = client.Index(collection_name)

    result = index.query(vector=embedding, top_k=n, include_metadata=True)
    matches = result.get("matches", [])

    if not matches:
        return ""

    return matches[0].get("metadata", {}).get("text", "")
