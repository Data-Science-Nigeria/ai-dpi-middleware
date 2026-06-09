"""Schema-constrained structured extraction endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import get_config
from app.middleware.rate_limit import rate_limit
from app.schemas.extract import ExtractionRequest, ExtractionResponse
from app.services.extraction import main as extraction_service
from app.services.chat.models.registry import DEFAULT_MODEL

router = APIRouter(prefix="/extract", tags=["Extraction"])

_rl = get_config().get("llm", {}).get("rate_limit", {})


@router.post(
    "",
    response_model=ExtractionResponse,
    summary="Extract structured data from text",
    description="""
Extract structured fields from free-form text using the LLM's native structured output.

**Provider behaviour**:
- `anthropic` — forced `tool_use`; guaranteed valid JSON
- `openai` — `json_schema` response format; guaranteed valid JSON
- `groq` — `json_object` mode + schema in system prompt
- `gemini` — `application/json` mime type + schema in prompt
- `ollama` — `format=json` + schema in system prompt (sovereign, no API key)

Output is validated against the supplied JSON Schema. If validation fails and
`max_retries > 0`, the error is fed back to the LLM for a corrected attempt.

**Example** — extract person fields:
```json
{
  "text": "Full name: Amina Kofi. Date of birth: 1990-03-15. ID: GH-12345.",
  "output_schema": {
    "type": "object",
    "properties": {
      "full_name":      { "type": "string" },
      "date_of_birth":  { "type": "string" },
      "id_number":      { "type": "string" }
    },
    "required": ["full_name", "id_number"]
  },
  "provider": "anthropic"
}
```
""",
)
async def extract(
    body: ExtractionRequest,
    _user: dict = Depends(rate_limit(part="chat", user_limit=_rl.get("user", 10), admin_limit=_rl.get("admin", 60))),
) -> ExtractionResponse:
    model = body.model or DEFAULT_MODEL.get(body.provider, "")

    data, valid, errors = await extraction_service.extract(
        text=body.text,
        output_schema=body.output_schema,
        provider=body.provider,
        model=model,
        max_retries=body.max_retries,
    )

    return ExtractionResponse(
        data=data,
        valid=valid,
        errors=errors,
        provider=body.provider,
        model=model,
    )
