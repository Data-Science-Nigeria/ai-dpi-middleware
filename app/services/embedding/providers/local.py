"""Local sentence-transformers embedding provider – sovereign deployment, no API calls."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from app.config import get_config


@lru_cache(maxsize=4)
def _model(model_name: str):
    """Load and cache a SentenceTransformer model (one per unique model name)."""
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    return SentenceTransformer(model_name)


async def get_embedding(text: str, model: str | None = None) -> list[float]:
    cfg = get_config()["llm"]["embedding_model"]
    model_name = model or cfg.get("model", "all-MiniLM-L6-v2")

    loop = asyncio.get_event_loop()
    # SentenceTransformer.encode is CPU/GPU-bound – run off the event loop
    vector: list[float] = await loop.run_in_executor(
        None,
        lambda: _model(model_name).encode([text], convert_to_numpy=True)[0].tolist(),
    )
    return vector
