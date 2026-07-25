"""Agentic loop — LLM reasons, calls tools, observes results, repeats until done.

Supports Anthropic (tool_use) and OpenAI-compatible providers (function calling).
Groq uses OpenAI-compatible function calling.
Gemini and Ollama fall back to single-shot: no tool calling loop, just a direct answer.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from app.config import get_config
from app.services.agent.tools import Tool, get_all, get
from app.services.metrics import llm_requests_total, llm_errors_total

MAX_ITERATIONS = 10  # hard cap to prevent runaway loops


# ── Anthropic ──────────────────────────────────────────────────────────────────

async def _execute_anthropic_tool_calls(
    tool_calls: list,
    trace: list[dict],
) -> list[dict]:
    """Execute Anthropic tool_use blocks, recording each in trace.

    Returns the tool_result blocks to append to the conversation.
    """
    tool_results = []
    for call in tool_calls:
        tool = get(call.name)
        if tool is None:
            result_content = f"Error: unknown tool '{call.name}'"
        else:
            trace.append({"tool": call.name, "input": call.input})
            try:
                result_content = await tool.fn(call.input)
            except Exception as exc:
                result_content = f"Tool error: {exc}"
            trace[-1]["output"] = result_content

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": result_content,
        })

    return tool_results


async def _run_anthropic(
    messages: list[dict],
    model: str,
    system: str | None,
    max_tokens: int,
    tools: list[Tool],
) -> tuple[str, list[dict]]:
    """Run agentic loop via Anthropic tool_use. Returns (final_text, trace)."""
    from app.providers.anthropic import get_client

    cfg = get_config()["llm"]["providers"]["anthropic"]
    client = get_client(cfg["api_key"])
    trace: list[dict] = []

    anthropic_tools = [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in tools
    ]

    msgs = list(messages)

    for _ in range(MAX_ITERATIONS):
        llm_requests_total.labels(provider="anthropic", model=model).inc()
        params: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": msgs,
            "tools": anthropic_tools,
        }
        if system:
            params["system"] = system

        try:
            response = await client.messages.create(**params)
        except Exception:
            llm_errors_total.labels(provider="anthropic").inc()
            raise

        # Collect all text and tool_use blocks
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_calls:
            # Done — return final text
            return "\n".join(b.text for b in text_blocks if b.text), trace

        # Append assistant message
        msgs.append({"role": "assistant", "content": response.content})

        # Execute each tool and build tool_result blocks
        tool_results = await _execute_anthropic_tool_calls(tool_calls, trace)

        msgs.append({"role": "user", "content": tool_results})

    return "Agent reached max iterations without a final answer.", trace


# ── OpenAI / Groq ──────────────────────────────────────────────────────────────

async def _execute_openai_tool_calls(
    tool_calls: list,
    trace: list[dict],
) -> list[dict]:
    """Execute OpenAI-compatible tool calls, recording each in trace.

    Returns the tool-role messages to append to the conversation.
    """
    tool_messages = []
    for call in tool_calls:
        fn_name = call.function.name
        try:
            params = json.loads(call.function.arguments)
        except json.JSONDecodeError:
            params = {}

        tool = get(fn_name)
        trace.append({"tool": fn_name, "input": params})
        if tool is None:
            result = f"Error: unknown tool '{fn_name}'"
        else:
            try:
                result = await tool.fn(params)
            except Exception as exc:
                result = f"Tool error: {exc}"
        trace[-1]["output"] = result

        tool_messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": result,
        })

    return tool_messages


async def _run_openai_compat(
    messages: list[dict],
    model: str,
    system: str | None,
    max_tokens: int,
    tools: list[Tool],
    provider: str,
) -> tuple[str, list[dict]]:
    """OpenAI function-calling compatible loop (works for openai + groq)."""
    import openai as _openai

    cfg = get_config()["llm"]["providers"][provider]
    client = _openai.AsyncOpenAI(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
    )
    trace: list[dict] = []

    oai_tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]

    msgs: list[dict] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    for _ in range(MAX_ITERATIONS):
        llm_requests_total.labels(provider=provider, model=model).inc()
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=msgs,
                tools=oai_tools,
                tool_choice="auto",
            )
        except Exception:
            llm_errors_total.labels(provider=provider).inc()
            raise

        msg = response.choices[0].message
        msgs.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content or "", trace

        msgs.extend(await _execute_openai_tool_calls(msg.tool_calls, trace))

    return "Agent reached max iterations without a final answer.", trace


# ── Fallback (Gemini / Ollama) ─────────────────────────────────────────────────

async def _run_fallback(
    messages: list[dict],
    model: str,
    system: str | None,
    max_tokens: int,
    provider: str,
    tools: list[Tool],
) -> tuple[str, list[dict]]:
    """Single-shot — no tool loop. Describe available tools in system prompt."""
    from app.services.chat import main as chat_service

    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description}" for t in tools
    )
    augmented_system = (
        (system or "You are a helpful AI assistant.")
        + f"\n\nAvailable capabilities (use them in your reasoning):\n{tool_descriptions}"
    )

    llm_requests_total.labels(provider=provider, model=model).inc()
    try:
        reply = await chat_service.chat(
            messages=messages,
            provider=provider,
            model=model,
            system=augmented_system,
            max_tokens=max_tokens,
        )
    except Exception:
        llm_errors_total.labels(provider=provider).inc()
        raise

    return reply, []


# ── Public entry point ─────────────────────────────────────────────────────────

async def run(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None = None,
    max_tokens: int = 2048,
    tool_names: list[str] | None = None,
) -> tuple[str, list[dict]]:
    """Run the agentic loop.

    Returns:
        (reply: str, trace: list[dict])
        trace contains one entry per tool call: {"tool", "input", "output"}
    """
    tools = get_all()
    if tool_names is not None:
        tools = [t for t in tools if t.name in tool_names]

    if provider == "anthropic":
        return await _run_anthropic(messages, model, system, max_tokens, tools)
    elif provider in ("openai", "groq"):
        return await _run_openai_compat(messages, model, system, max_tokens, tools, provider)
    else:
        return await _run_fallback(messages, model, system, max_tokens, provider, tools)
