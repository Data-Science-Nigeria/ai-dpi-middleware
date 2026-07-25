"""Translation endpoint – LLM-backed, model-agnostic."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.chat import main as chat_service
from app.services.chat.models.registry import DEFAULT_MODEL

router = APIRouter(prefix="/translate", tags=["Translation"])

_rl = get_config().get("llm", {}).get("rate_limit", {})


def _build_prompt(text: str, source: str | None, target: str) -> str:
    src_clause = f"from {source}" if source else "(auto-detect source language)"
    return (
        f"Translate the following text {src_clause} to {target}. "
        "Return only the translated text with no explanation, preamble, or markdown.\n\n"
        f"{text}"
    )


@router.post(
    "",
    summary="Translate text",
    description="""
Translate text between any languages using any configured LLM provider.

- **source_language**: BCP-47 code (`en`, `fr`, `yo`, `sw`, …). Omit for auto-detection.
- **target_language**: Required. BCP-47 code of the desired output language.
- **provider**: `anthropic` (default), `openai`, `groq`, `gemini`.
- **model**: Omit to use the provider default.

All LLM providers support 100+ languages. For African language pairs (Yoruba, Hausa,
Igbo, Swahili, Amharic, etc.) use Claude or Gemini for best results.
""",
)
async def translate(
    body: TranslateRequest,
    _user: Annotated[dict, Depends(rate_limit(part="chat", user_limit=_rl.get("user", 10), admin_limit=_rl.get("admin", 60)))],
) -> TranslateResponse:
    model = body.model or DEFAULT_MODEL.get(body.provider, "")

    prompt = _build_prompt(body.text, body.source_language, body.target_language)

    translation = await chat_service.chat(
        messages=[{"role": "user", "content": prompt}],
        provider=body.provider,
        model=model,
        max_tokens=body.max_tokens,
    )

    return TranslateResponse(
        translation=translation.strip(),
        source_language=body.source_language,
        target_language=body.target_language,
        provider=body.provider,
        model=model,
    )
