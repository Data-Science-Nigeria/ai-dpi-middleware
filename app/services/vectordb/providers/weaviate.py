"""Vector DB provider — Weaviate (open-source / managed).

Supports local Docker (http), Weaviate Cloud (wcs), and embedded modes.
Uses the v4 Python client with async support.
"""

from __future__ import annotations

import uuid

import weaviate
import weaviate.classes as wvc
from weaviate.classes.query import MetadataQuery

from app.config import get_config

_client: weaviate.WeaviateClient | None = None


def get_client() -> weaviate.WeaviateClient:
    global _client
    if _client is None or not _client.is_connected():
        cfg = get_config()["llm"]["vector_database"]
        mode = cfg.get("type", "http")

        if mode == "http":
            _client = weaviate.connect_to_local(
                host=cfg.get("http_host", "localhost"),
                port=cfg.get("http_port", 8080),
                grpc_port=cfg.get("grpc_port", 50051),
            )
        elif mode == "cloud":
            _client = weaviate.connect_to_weaviate_cloud(
                cluster_url=cfg["cloud_host"],
                auth_credentials=weaviate.auth.AuthApiKey(cfg["API_KEY"]),
            )
        elif mode == "embedded":
            _client = weaviate.connect_to_embedded()
        else:
            raise ValueError(f"Unsupported Weaviate connection type: {mode!r}")

    return _client


def _class_name(collection_name: str) -> str:
    """Weaviate class names must be PascalCase and start with a letter."""
    name = "".join(w.capitalize() for w in collection_name.replace("-", "_").split("_"))
    return name if name[0].isalpha() else f"C{name}"


async def add(
    collection_name: str,
    embeddings: list[list[float]],
    documents: list[str],
    meta_data: list[dict] | None = None,
) -> None:
    if len(embeddings) != len(documents):
        raise ValueError("embeddings and documents must have the same length")

    client = get_client()
    cls = _class_name(collection_name)

    if not client.collections.exists(cls):
        client.collections.create(
            name=cls,
            vectorizer_config=wvc.config.Configure.Vectorizer.none(),
            properties=[
                wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
            ],
        )

    collection = client.collections.get(cls)
    objects = []
    for i, (doc, emb) in enumerate(zip(documents, embeddings)):
        props = {"text": doc}
        if meta_data and i < len(meta_data):
            props.update(meta_data[i])
        objects.append(
            wvc.data.DataObject(
                properties=props,
                vector=emb,
                uuid=uuid.uuid4(),
            )
        )

    collection.data.insert_many(objects)


async def retrieve(
    embedding: list[float],
    collection_name: str,
    n_results: int | None = None,
) -> str:
    cfg = get_config()["llm"]["vector_database"]
    n = n_results or cfg.get("N_RESULT", 2)
    client = get_client()
    cls = _class_name(collection_name)

    collection = client.collections.get(cls)
    result = collection.query.near_vector(
        near_vector=embedding,
        limit=n,
        return_metadata=MetadataQuery(distance=True),
    )

    if not result.objects:
        return ""

    return result.objects[0].properties.get("text", "")
