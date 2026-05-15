"""Vector DB provider — Qdrant (open-source + managed cloud).

Supports self-hosted Docker (http) and Qdrant Cloud (https + api_key).
Uses qdrant-client v1.12+ with async operations via run_in_executor.
"""

from __future__ import annotations

import asyncio
import uuid
from functools import partial

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import get_config

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        cfg = get_config()["llm"]["vector_database"]
        mode = cfg.get("type", "http")

        if mode == "cloud":
            _client = QdrantClient(
                url=cfg["cloud_host"],
                api_key=cfg["API_KEY"],
            )
        elif mode == "http":
            _client = QdrantClient(
                host=cfg.get("http_host", "localhost"),
                port=cfg.get("http_port", 6333),
            )
        elif mode == "memory":
            _client = QdrantClient(":memory:")
        else:
            raise ValueError(f"Unsupported Qdrant connection type: {mode!r}")

    return _client


def _ensure_collection(client: QdrantClient, collection_name: str, dim: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=dim,
                distance=qmodels.Distance.COSINE,
            ),
        )


async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
) -> None:
    if len(embeddings) != len(documents):
        raise ValueError("embeddings and documents must have the same length")

    client = get_client()
    dim = len(embeddings[0])

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_ensure_collection, client, collection_name, dim))

    points = []
    for i, (doc, emb) in enumerate(zip(documents, embeddings)):
        payload = {"text": doc}
        if meta_data and i < len(meta_data):
            payload.update(meta_data[i])
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload=payload,
            )
        )

    await loop.run_in_executor(
        None,
        partial(client.upsert, collection_name=collection_name, points=points),
    )


async def retrieve(
    embedding: list[float],
    collection_name: str,
    n_results: int | None = None,
) -> str:
    cfg = get_config()["llm"]["vector_database"]
    n = n_results or cfg.get("N_RESULT", 2)

    client = get_client()
    loop = asyncio.get_event_loop()

    results = await loop.run_in_executor(
        None,
        partial(
            client.search,
            collection_name=collection_name,
            query_vector=embedding,
            limit=n,
            with_payload=True,
        ),
    )

    if not results:
        return ""

    return results[0].payload.get("text", "")
