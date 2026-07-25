"""Chat provider – generic OpenAI-compatible API."""

from __future__ import annotations

import aiohttp

from app.config import get_config

async def get_embedding(text: str, model: str | None = None):
    cfg = get_config()["llm"]["embedding_model"]
    print(cfg)

    url = cfg.get("base_url", "https://api.openai.com/v1/embeddings")

    payload = {
        "input": text,
        "model": model or cfg.get("model", "text-embedding-3-small"),
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            url,
            headers=_headers(cfg["API_KEY"]),
            json=payload,
        ) as response:

            if response.status >= 400:
                print("Embedding error:", await response.text())
                response.raise_for_status()

            data = await response.json()

            return data["data"][0]["embedding"]
            
def _headers(api_key: str) -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

