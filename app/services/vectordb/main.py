from __future__ import annotations

from app.config import get_config
from app.services.vectordb.providers import pinecone as pinecone_provider
from app.services.vectordb.providers import qdrant as qdrant_provider
from app.services.vectordb.providers import weaviate as weaviate_provider

_PROVIDERS = {
    "weaviate": weaviate_provider,   # default — self-hosted Docker or Weaviate Cloud
    "pinecone": pinecone_provider,   # managed cloud
    "qdrant": qdrant_provider,       # self-hosted Docker or Qdrant Cloud
}


def _provider():
    name = get_config()["llm"]["vector_database"]["provider"]
    p = _PROVIDERS.get(name)
    if p is None:
        raise ValueError(
            f"Unsupported vector_database provider: {name!r}. "
            f"Supported: {sorted(_PROVIDERS)}."
        )
    return p


async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
) -> None:
    await _provider().add(
        collection_name=collection_name,
        embeddings=embeddings,
        documents=documents,
        meta_data=meta_data,
    )


async def retrieve(
    embedding: list[float],
    collection_name: str,
    n_result: int = 2,
) -> str:
    return await _provider().retrieve(
        embedding=embedding,
        collection_name=collection_name,
        n_results=n_result,
    )
