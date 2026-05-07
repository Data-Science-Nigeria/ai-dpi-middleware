import uuid

import chromadb

from app.config import get_config

_client = None


def get_client():
    global _client
    if _client is None:
        cfg = get_config()["llm"]["vector_database"]
        client_type = cfg.get("type", "ephemeral")

        if client_type == "cloud":
            _client = chromadb.CloudClient(
                cloud_host=cfg["cloud_host"],
                cloud_port=cfg["cloud_port"],
                api_key=cfg["API_KEY"],
                tenant=cfg["tenant"],
                database=cfg["database"],
            )
        elif client_type == "persistent":
            _client = chromadb.PersistentClient(path=cfg["path"])
        elif client_type == "ephemeral":
            _client = chromadb.Client()
        elif client_type == "http":
            _client = chromadb.HttpClient(
                host=cfg["http_host"],
                port=cfg["http_port"],
            )
        else:
            raise ValueError(f"Unsupported vector_database type: {client_type!r}")

    return _client


async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
):
    if len(embeddings) != len(documents):
        raise ValueError("embeddings and documents must have the same length")
    if meta_data is not None and len(meta_data) != len(documents):
        raise ValueError("meta_data and documents must have the same length")

    client = get_client()
    collection = client.get_or_create_collection(collection_name)

    ids = [str(uuid.uuid4()) for _ in documents]

    collection.add(
        ids=ids,
        embeddings=embeddings, # type: ignore
        documents=documents,
        metadatas=meta_data, # type: ignore
    )


async def retrieve(
    embedding: list[float],
    collection_name: str,
    n_results: int | None = None,
):
    cfg = get_config()["llm"]["vector_database"]
    client = get_client()
    collection = client.get_collection(collection_name)

    document = collection.query(
        query_embeddings=[embedding],
        n_results=n_results or cfg.get("N_RESULT", 2),
    )['documents']

    if document is not None:
        return document[0][0]
