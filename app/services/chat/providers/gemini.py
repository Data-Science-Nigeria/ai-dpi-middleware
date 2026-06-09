"""Chat provider — Google Gemini via google-genai SDK."""

from __future__ import annotations

from google import genai
from google.genai import types

from app.config import get_config

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = get_config()["llm"]["providers"]["gemini"]["api_key"]
        _client = genai.Client(api_key=api_key)
    return _client


def _build_contents(messages: list[dict]) -> list[types.Content]:
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    return contents


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    client = _get_client()
    cfg = get_config()["llm"]["providers"]["gemini"]
    contents = _build_contents(messages)

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=cfg.get("kwargs", {}).get("temperature", 0.9),
        top_p=cfg.get("kwargs", {}).get("top_p", 0.95),
        system_instruction=system,
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return response.text


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
):
    client = _get_client()
    cfg = get_config()["llm"]["providers"]["gemini"]
    contents = _build_contents(messages)

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=cfg.get("kwargs", {}).get("temperature", 0.9),
        top_p=cfg.get("kwargs", {}).get("top_p", 0.95),
        system_instruction=system,
    )

    async for chunk in await client.aio.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.text:
            yield chunk.text
