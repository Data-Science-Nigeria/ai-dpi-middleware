"""Built-in DPI tool registry for the agent loop.

Each tool exposes:
  - name           : unique snake_case identifier
  - description    : shown to the LLM so it knows when to call the tool
  - input_schema   : JSON Schema for the tool's parameters
  - callable       : async fn(params: dict) -> str  (always returns plain text / JSON string)

The LLM receives all registered tools on every agent invocation and decides which to call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[[dict], Awaitable[str]]


_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> None:
    _REGISTRY[tool.name] = tool


def get_all() -> list[Tool]:
    return list(_REGISTRY.values())


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


# ── Built-in tools ─────────────────────────────────────────────────────────────

async def _search_documents(params: dict) -> str:
    from app.services.embedding.main import get_embedding
    from app.services.vectordb.main import retrieve
    from app.config import get_config

    query = params["query"]
    cfg = get_config()
    collection = params.get("collection") or cfg["llm"]["vector_database"].get("collection_name", "default_collection")
    n = int(params.get("n_results", cfg["llm"]["vector_database"].get("N_RESULT", 3)))

    embedding = await get_embedding(text=query)
    result = await retrieve(embedding=embedding, collection_name=collection, n_result=n)
    return result or "No relevant documents found."


async def _translate_text(params: dict) -> str:
    from app.services.chat import main as chat_service
    from app.services.chat.models.registry import DEFAULT_MODEL

    text = params["text"]
    target = params["target_language"]
    source = params.get("source_language")
    provider = params.get("provider", "anthropic")
    model = params.get("model") or DEFAULT_MODEL.get(provider, "")

    src_clause = f"from {source}" if source else "(auto-detect source language)"
    prompt = (
        f"Translate the following text {src_clause} to {target}. "
        "Return only the translated text with no explanation.\n\n"
        f"{text}"
    )
    return await chat_service.chat(
        messages=[{"role": "user", "content": prompt}],
        provider=provider,
        model=model,
        max_tokens=2048,
    )


async def _extract_fields(params: dict) -> str:
    from app.services.extraction import main as extraction_service
    from app.services.chat.models.registry import DEFAULT_MODEL

    text = params["text"]
    output_schema = params["output_schema"]
    provider = params.get("provider", "anthropic")
    model = params.get("model") or DEFAULT_MODEL.get(provider, "")

    data, valid, errors = await extraction_service.extract(
        text=text,
        output_schema=output_schema,
        provider=provider,
        model=model,
        max_retries=1,
    )
    return json.dumps({"data": data, "valid": valid, "errors": errors})


async def _http_request(params: dict) -> str:
    import httpx

    method = params.get("method", "GET").upper()
    url = params["url"]
    headers = params.get("headers", {})
    body = params.get("body")
    timeout = float(params.get("timeout_seconds", 10))

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers, json=body)
        try:
            return json.dumps(response.json())
        except Exception:
            return response.text


# Register all built-ins
register(Tool(
    name="search_documents",
    description=(
        "Search the document knowledge base for information relevant to a query. "
        "Use when the user asks about stored documents, policies, guidelines, or any knowledge that may have been ingested."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "collection": {"type": "string", "description": "Collection name (optional, uses default if omitted)"},
            "n_results": {"type": "integer", "description": "Number of results to return (default 3)", "default": 3},
        },
        "required": ["query"],
    },
    fn=_search_documents,
))

register(Tool(
    name="translate_text",
    description=(
        "Translate text from one language to another. "
        "Supports 100+ languages including African languages (Yoruba, Hausa, Igbo, Swahili, Amharic)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate"},
            "target_language": {"type": "string", "description": "Target language BCP-47 code (e.g. 'fr', 'yo', 'sw')"},
            "source_language": {"type": "string", "description": "Source language BCP-47 code. Omit for auto-detect."},
        },
        "required": ["text", "target_language"],
    },
    fn=_translate_text,
))

register(Tool(
    name="extract_fields",
    description=(
        "Extract structured fields from unstructured text using a JSON Schema. "
        "Use when you need to pull typed data (names, IDs, dates, amounts) from free-form text."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Source text to extract from"},
            "output_schema": {
                "type": "object",
                "description": "JSON Schema describing the fields to extract",
            },
        },
        "required": ["text", "output_schema"],
    },
    fn=_extract_fields,
))

register(Tool(
    name="http_request",
    description=(
        "Make an HTTP request to an external API. "
        "Use for external lookups: NIN verification, BVN check, registry queries, webhook notifications."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL to call"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
            "headers": {"type": "object", "description": "HTTP headers as key-value pairs"},
            "body": {"type": "object", "description": "Request body (sent as JSON)"},
            "timeout_seconds": {"type": "number", "default": 10},
        },
        "required": ["url"],
    },
    fn=_http_request,
))
