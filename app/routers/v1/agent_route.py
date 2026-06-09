"""Agent endpoint — multi-step LLM reasoning with built-in DPI tools."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.agent import AgentRequest, AgentResponse, ToolCall
from app.services.agent import loop as agent_loop
from app.services.agent.tools import get_all
from app.services.chat.models.registry import DEFAULT_MODEL

router = APIRouter(prefix="/agent", tags=["Agent"])

_rl = get_config().get("llm", {}).get("rate_limit", {})


@router.post(
    "/run",
    response_model=AgentResponse,
    summary="Run agent",
    description="""
Run a multi-step AI agent that can use built-in DPI tools to complete a goal.

The agent receives your messages, decides which tools to call (document search,
translation, field extraction, HTTP requests), executes them, and iterates until
it produces a final answer — all in one request.

**Tool-calling support by provider:**
- `anthropic` — full tool-use loop (recommended)
- `openai` / `groq` — full function-calling loop
- `gemini` / `ollama` — single-shot (tools described in prompt, no execution loop)

**Available built-in tools:** search_documents, translate_text, extract_fields, http_request
""",
)
async def run_agent(
    body: AgentRequest,
    _user: dict = Depends(rate_limit(part="chat", user_limit=_rl.get("user", 10), admin_limit=_rl.get("admin", 60))),
) -> AgentResponse:
    model = body.model or DEFAULT_MODEL.get(body.provider, "")

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        reply, trace = await agent_loop.run(
            messages=messages,
            provider=body.provider,
            model=model,
            system=body.system,
            max_tokens=body.max_tokens,
            tool_names=body.tools,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return AgentResponse(
        reply=reply,
        provider=body.provider,
        model=model,
        tool_calls=[ToolCall(**t) for t in trace],
        iterations=len(trace),
    )


@router.get(
    "/tools",
    summary="List available agent tools",
    description="Returns all built-in tools the agent can call, with their descriptions and input schemas.",
)
async def list_tools(
    _user: dict = Depends(rate_limit(part="chat", user_limit=_rl.get("user", 10), admin_limit=_rl.get("admin", 60))),
) -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in get_all()
    ]
