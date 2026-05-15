"""Chat provider — Google Gemini via google-generativeai SDK."""

from __future__ import annotations

import google.generativeai as genai

from app.config import get_config

_configured = False


def _configure() -> None:
    global _configured
    if not _configured:
        api_key = get_config()["llm"]["providers"]["gemini"]["api_key"]
        genai.configure(api_key=api_key)
        _configured = True


def _build_contents(messages: list[dict], system: str | None) -> tuple[list, str | None]:
    """Convert OpenAI-style messages to Gemini contents format."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    return contents, system


async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    _configure()
    cfg = get_config()["llm"]["providers"]["gemini"]
    contents, sys_instruction = _build_contents(messages, system)

    generation_config = genai.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=cfg.get("kwargs", {}).get("temperature", 0.9),
        top_p=cfg.get("kwargs", {}).get("top_p", 0.95),
    )

    model_obj = genai.GenerativeModel(
        model_name=model,
        system_instruction=sys_instruction,
        generation_config=generation_config,
    )

    response = await model_obj.generate_content_async(contents)
    return response.text


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
):
    _configure()
    cfg = get_config()["llm"]["providers"]["gemini"]
    contents, sys_instruction = _build_contents(messages, system)

    generation_config = genai.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=cfg.get("kwargs", {}).get("temperature", 0.9),
        top_p=cfg.get("kwargs", {}).get("top_p", 0.95),
    )

    model_obj = genai.GenerativeModel(
        model_name=model,
        system_instruction=sys_instruction,
        generation_config=generation_config,
    )

    async for chunk in await model_obj.generate_content_async(contents, stream=True):
        if chunk.text:
            yield chunk.text
