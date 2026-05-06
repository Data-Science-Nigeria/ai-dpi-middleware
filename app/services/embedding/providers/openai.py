"""Chat provider — generic OpenAI-compatible API."""

from __future__ import annotations

import aiohttp

from app.config import get_config


async def get_embedding(
    text: str,
    model: str,
):
    cfg = get_config()["llm"]["embedding_model"]

    resolved_url = "https://api.openai.com/v1/embeddings"
    payload = {
        "input": text,
        "model": model
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            resolved_url, headers=_headers(cfg["api_key"]), json=payload
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data['data'][0]['embedding']
            
def _headers(api_key: str) -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

