"""Schema-constrained extraction service.

Routes to provider-native structured output where available:
  - Anthropic: tool_use with forced tool_choice → guaranteed JSON
  - OpenAI:    response_format json_schema → guaranteed JSON
  - Groq:      response_format json_object + schema in system prompt
  - Gemini:    response_mime_type application/json + schema in prompt
  - Ollama:    format=json + schema in system prompt

All paths validate the result against the caller-supplied JSON Schema.
On validation failure, retries once with the error fed back to the LLM.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from app.config import get_config
from app.core.logging import logger
from app.services.chat.models.registry import DEFAULT_MODEL


async def extract(
    text: str,
    output_schema: dict[str, Any],
    provider: str,
    model: str | None,
    max_retries: int = 1,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Extract structured data from *text* conforming to *output_schema*.

    Returns (data, valid, errors).
    """
    model = model or DEFAULT_MODEL.get(provider, "")
    schema_str = json.dumps(output_schema, indent=2)

    for attempt in range(max_retries + 1):
        feedback = f"\n\nPrevious attempt failed validation. Fix these errors:\n{_last_errors}" \
            if attempt > 0 else ""

        raw = await _call_provider(provider, model, text, schema_str, feedback)
        data, errors = _parse_and_validate(raw, output_schema)

        if not errors:
            return data, True, []

        _last_errors = "\n".join(errors)
        logger.warning(f"Extraction attempt {attempt + 1} failed validation: {_last_errors}")

    return data, False, errors  # type: ignore[possibly-undefined]


# ── Provider dispatch ─────────────────────────────────────────────────────────

async def _call_provider(
    provider: str,
    model: str,
    text: str,
    schema_str: str,
    feedback: str,
) -> str:
    if provider == "anthropic":
        return await _anthropic(model, text, schema_str, feedback)
    if provider == "openai":
        return await _openai(model, text, schema_str, feedback)
    if provider == "groq":
        return await _groq(model, text, schema_str, feedback)
    if provider == "gemini":
        return await _gemini(model, text, schema_str, feedback)
    if provider == "ollama":
        return await _ollama(model, text, schema_str, feedback)
    raise ValueError(f"Unsupported provider: {provider!r}")


async def _anthropic(model: str, text: str, schema_str: str, feedback: str) -> str:
    import anthropic
    cfg = get_config()["llm"]["providers"]["anthropic"]
    client = anthropic.AsyncAnthropic(api_key=cfg["api_key"])

    tool = {
        "name": "extract_data",
        "description": "Extract structured data from the provided text.",
        "input_schema": json.loads(schema_str),
    }
    msg = await client.messages.create(
        model=model,
        max_tokens=cfg.get("max_tokens", 2048),
        tools=[tool],
        tool_choice={"type": "tool", "name": "extract_data"},
        messages=[{
            "role": "user",
            "content": f"Extract structured data from this text:\n\n{text}{feedback}",
        }],
    )
    for block in msg.content:
        if block.type == "tool_use":
            return json.dumps(block.input)
    return "{}"


async def _openai(model: str, text: str, schema_str: str, feedback: str) -> str:
    from openai import AsyncOpenAI
    cfg = get_config()["llm"]["providers"]["openai"]
    client = AsyncOpenAI(api_key=cfg["api_key"])

    resp = await client.chat.completions.create(
        model=model,
        max_tokens=cfg.get("max_tokens", 2048),
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extracted_data",
                "strict": True,
                "schema": json.loads(schema_str),
            },
        },
        messages=[
            {"role": "system", "content": "You extract structured data and return valid JSON only."},
            {"role": "user", "content": f"Extract from this text:\n\n{text}{feedback}"},
        ],
    )
    return resp.choices[0].message.content or "{}"


async def _groq(model: str, text: str, schema_str: str, feedback: str) -> str:
    from groq import AsyncGroq
    cfg = get_config()["llm"]["providers"]["groq"]
    client = AsyncGroq(api_key=cfg["api_key"])

    resp = await client.chat.completions.create(
        model=model,
        max_tokens=cfg.get("max_tokens", 2048),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured data and return valid JSON only. "
                    f"Output must conform to this schema:\n{schema_str}"
                ),
            },
            {"role": "user", "content": f"Extract from this text:\n\n{text}{feedback}"},
        ],
    )
    return resp.choices[0].message.content or "{}"


async def _gemini(model: str, text: str, schema_str: str, feedback: str) -> str:
    from google import genai
    from google.genai import types
    cfg = get_config()["llm"]["providers"]["gemini"]
    client = genai.Client(api_key=cfg["api_key"])

    prompt = (
        f"Extract structured data from the text below. "
        f"Return ONLY valid JSON conforming to this schema:\n{schema_str}\n\n"
        f"Text:\n{text}{feedback}"
    )
    config = types.GenerateContentConfig(response_mime_type="application/json")
    resp = await client.aio.models.generate_content(model=model, contents=prompt, config=config)
    return resp.text or "{}"


async def _ollama(model: str, text: str, schema_str: str, feedback: str) -> str:
    import httpx
    cfg = get_config()["llm"]["providers"]["ollama"]
    base_url = cfg.get("base_url", "http://localhost:11434")

    payload = {
        "model": model,
        "format": "json",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract structured data and return valid JSON only. "
                    f"Output must conform to this schema:\n{schema_str}"
                ),
            },
            {"role": "user", "content": f"Extract from this text:\n\n{text}{feedback}"},
        ],
    }
    async with httpx.AsyncClient(timeout=cfg.get("timeout_seconds", 120.0)) as client:
        resp = await client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ── Validation ────────────────────────────────────────────────────────────────

def _parse_and_validate(
    raw: str,
    schema: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {}, [f"Invalid JSON: {e}"]

    errors: list[str] = []
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(e.message)
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")

    return data, errors
