from app.config import get_config
from app.services.vectordb.providers import chroma as chroma_provider

async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
):
    provider = get_config()["llm"]["vector_database"]['provider']
    if provider == "chroma":
        return await chroma_provider.add(
            collection_name=collection_name,
            embeddings=embeddings,
            documents=documents,
            meta_data=meta_data
        )
    raise ValueError(f"Unsupported provider: {provider!r}")

async def retrieve(
    embedding,
    collection_name: str,
    n_result: int = 2,
):
    provider = get_config()["llm"]["vector_database"]['provider']
    if provider == "chroma":
        return await chroma_provider.retrieve(
            n_results=n_result,
            embedding=embedding,
            collection_name=collection_name
        )
    raise ValueError(f"Unsupported provider: {provider!r}")