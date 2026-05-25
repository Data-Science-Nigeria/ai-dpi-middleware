# AI-DPI Middleware — Implementation Plan

This document tracks what has been built, what is pending, and the full step-by-step walkthrough for implementing every remaining feature proposed in the AI-DPI proposal.

---

## Current State (as of this writing)

### Completed

| Feature | Files |
|---|---|
| FastAPI core, auth (JWT/OIDC/RBAC), rate limiting, audit logging | `app/main.py`, `app/auth/`, `app/middleware/` |
| LLM chat + streaming — Anthropic, OpenAI, Groq, Gemini, Generic | `app/services/chat/` |
| LLM translation (LLM-backed, 100+ languages) | `app/routers/v1/translate_route.py` |
| Speech-to-Text — OpenAI, Groq, Deepgram, Spitch, Intron | `app/services/stt/` |
| Text-to-Speech — OpenAI, ElevenLabs, Groq, Spitch, Intron | `app/services/tts/` |
| Embeddings — OpenAI (cloud) + sentence-transformers (local/sovereign) | `app/services/embedding/` |
| Vector DB — Weaviate, Qdrant, Pinecone | `app/services/vectordb/` |
| **RAG ingestion pipeline** — PDF, Office, image, plain text | `app/services/document/pipeline.py` |
| **OCR pipeline** — native PDF text, Tesseract, LLM vision fallback | `app/services/document/ocr.py` |
| **Office/knowledge format extractors** — DOCX, PPTX, XLSX, CSV, RTF, ODT, TXT, MD | `app/services/document/extractors.py` |
| **Text chunker** — sentence-aware, configurable overlap | `app/services/document/chunker.py` |
| **Document ingestion API** — `POST /v1/documents/ingest` | `app/routers/v1/document_route.py` |
| **Sovereign LLM** — Ollama (any open-weight model, fully local) | `app/services/chat/providers/ollama.py` |
| **Sovereign embeddings** — sentence-transformers (no API key) | `app/services/embedding/providers/local.py` |
| **Sovereign vector DB** — Weaviate in Docker (already existed) | `docker-compose.yml` (Weaviate service added) |
| **Docker sovereign stack** — Weaviate + Ollama + Redis | `docker-compose.yml` |
| Schema-constrained extraction — `POST /v1/extract`, provider-native structured output, jsonschema validation, retry on failure | `app/services/extraction/main.py`, `app/routers/v1/extract_route.py`, `app/schemas/extract.py` |
| Session / conversation history — Redis-backed per-session multi-turn history, configurable TTL + history_limit, GET/DELETE management endpoints | `app/services/session.py`, `app/routers/v1/chat_route.py` |

---

## Pending Features (Proposal → Implementation)

### 1. Agent & Tool Execution Runtime

**What the proposal says**: "agent and tool execution runtimes"

**What to build**: A lightweight agentic loop that lets the LLM call configured tools (functions) and iterate until it reaches a final answer. This is the backbone of use-cases like automated eligibility checking, document Q&A with follow-up queries, and fraud detection workflows.

**Implementation walkthrough**:

#### Step 1 — Define the tool registry (`app/services/agent/tools/registry.py`)
```python
# A tool is: name, description, JSON schema for parameters, async callable
TOOL_REGISTRY: dict[str, ToolDef] = {}

def register_tool(name, description, parameters_schema, fn):
    TOOL_REGISTRY[name] = ToolDef(name=name, description=description, schema=parameters_schema, fn=fn)
```

#### Step 2 — Ship built-in DPI tools (`app/services/agent/tools/builtin.py`)
Start with:
- `search_documents(query: str, collection: str)` — calls the RAG retrieval pipeline
- `transcribe_audio(file_path: str)` — calls the STT service
- `translate_text(text: str, target_language: str)` — calls the translation service
- `extract_document(file_path: str)` — calls the OCR pipeline

#### Step 3 — Implement the agentic loop (`app/services/agent/main.py`)
```python
async def run_agent(
    messages: list[dict],
    tools: list[str],          # names from TOOL_REGISTRY
    provider: str,
    model: str,
    max_iterations: int = 5,
) -> AgentResult:
    # 1. Build tool definitions for the LLM
    # 2. Send messages + tools to LLM
    # 3. If LLM returns tool_call → execute tool → append result → loop
    # 4. If LLM returns text → return final answer
    # 5. If max_iterations exceeded → return partial result with warning
```
Use provider-native tool calling:
- Anthropic: `tools=` parameter with `tool_use` / `tool_result` message blocks
- OpenAI/Groq: `tools=` with `function` calling
- Ollama: use prompt engineering + JSON mode (no native tool calling in most models)

#### Step 4 — Add the agent API endpoint (`app/routers/v1/agent_route.py`)
```
POST /v1/agent/run
{
  "messages": [...],
  "tools": ["search_documents", "translate_text"],
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "max_iterations": 5
}
```

#### Step 5 — Register in `app/routers/v1/base.py`

**Effort**: ~3–4 days  
**Dependencies**: existing chat and RAG services  
**Key schema files to create**: `app/schemas/agent.py`

---

### 2. Workflow Orchestration

**What the proposal says**: "workflow orchestration" and "event-driven integrations"

**What to build**: Named, reusable multi-step pipelines that chain services together. Example: "onboarding workflow" = STT → translate → extract fields from transcript → store in vector DB → notify via webhook.

**Implementation walkthrough**:

#### Step 1 — Define a workflow DSL in YAML (`app/services/workflow/schema.py`)
```yaml
# Example: document_onboarding.yaml
name: document_onboarding
steps:
  - id: ocr
    type: document_ingest
    input: "{{file}}"
    collection: "onboarding_docs"

  - id: extract
    type: chat
    provider: anthropic
    prompt: "Extract: name, date_of_birth, ID number from: {{ocr.text}}"
    output_schema:
      name: str
      date_of_birth: str
      id_number: str

  - id: translate
    type: translate
    input: "{{extract.output}}"
    target_language: "{{request.language}}"
```

#### Step 2 — Build the workflow executor (`app/services/workflow/executor.py`)
- Load workflow YAML from config or request body
- Execute steps in dependency order (topological sort)
- Each step receives outputs of previous steps as template variables
- Steps that don't depend on each other can run concurrently (`asyncio.gather`)

#### Step 3 — Add webhook output support (`app/services/workflow/webhook.py`)
```python
async def dispatch(url: str, payload: dict, secret: str | None) -> None:
    # HMAC-sign payload with secret if provided
    # POST to webhook URL with retry logic (3 attempts, exponential backoff)
```

#### Step 4 — Add workflow API endpoint (`app/routers/v1/workflow_route.py`)
```
POST /v1/workflow/run
{ "workflow": "document_onboarding", "inputs": { "file": "<base64>", "language": "fr" } }

POST /v1/workflow/run/inline   # run a workflow defined in the request body
```

**Effort**: ~1 week  
**Key design decision**: Start with sequential execution; add DAG/parallel execution as a follow-up.

---

### 3. Human-in-the-Loop

**What the proposal says**: "human-in-the-loop mechanisms" for high-assurance public-sector use cases

**What to build**: A review queue where agent/workflow outputs above a confidence threshold are automatically approved, and low-confidence outputs are held for human review before being released.

**Implementation walkthrough**:

#### Step 1 — Review queue model (`app/services/hitl/queue.py`)
Store pending reviews in Redis (or Postgres for durability):
```
Key: hitl:{review_id}
Value: { status: "pending" | "approved" | "rejected", output: {...}, reviewer: str, timestamp: ... }
```

#### Step 2 — Confidence scoring (`app/services/hitl/confidence.py`)
- For structured extraction: check that all required fields are populated
- For RAG answers: use vector similarity score of top-retrieved chunk as proxy
- Configurable threshold per workflow step

#### Step 3 — Review API (`app/routers/v1/hitl_route.py`)
```
GET  /v1/hitl/pending                    # list pending reviews (admin only)
GET  /v1/hitl/{review_id}               # get a specific review item
POST /v1/hitl/{review_id}/approve       # approve with optional edit
POST /v1/hitl/{review_id}/reject        # reject with reason
```

#### Step 4 — Integrate into workflow executor
After each step, check confidence. If below threshold, pause workflow, enqueue review, return `{ status: "pending_review", review_id: "..." }` to caller.

**Effort**: ~3 days  
**Dependencies**: workflow orchestration (#2), Redis

---

### 4. Content Guardrails & Safety Filters

**What the proposal says**: "guardrails" for high-assurance public-sector use cases

**What to build**: Middleware layer that screens both inputs (prompt injection, PII, policy violations) and outputs (hallucination indicators, disallowed content) before they are returned to callers.

**Implementation walkthrough**:

#### Step 1 — Input guardrails (`app/services/guardrails/input.py`)
- **Prompt injection detection**: regex + LLM-based detection of instruction-override attempts
- **PII scrubbing** (optional): detect and redact names, IDs, phone numbers before sending to external LLMs using `presidio-anonymizer` or simple regex patterns
- **Policy keyword filter**: configurable blocklist per deployment

#### Step 2 — Output guardrails (`app/services/guardrails/output.py`)
- **Hallucination signal**: if RAG context was provided and the answer contains claims not found in context, flag with low-confidence metadata
- **Length / format validation**: for schema-constrained extraction, validate output against expected JSON schema
- **Content policy filter**: configurable blocklist on outputs

#### Step 3 — Config (`default_config.yaml`)
```yaml
guardrails:
  enabled: true
  input:
    detect_prompt_injection: true
    pii_scrubbing: false          # set true for health/identity deployments
    blocklist: []
  output:
    validate_against_context: true
    hallucination_flag_threshold: 0.3
    blocklist: []
```

#### Step 4 — Wire into chat route and agent route
Wrap `chat_service.chat()` calls with `guardrails.screen_input()` and `guardrails.screen_output()`.

**Effort**: ~3–4 days  
**Key library**: `presidio-analyzer` + `presidio-anonymizer` for PII (optional, heavy dependency)

---

### ✅ DONE — 5. Schema-Constrained Extraction Mode

**What the proposal says**: "schema-constrained extraction modes"

**What to build**: An endpoint that takes a document (or raw text) plus a JSON schema and extracts structured data matching that schema, using the LLM's structured output / JSON mode.

**Implementation walkthrough**:

#### Step 1 — Add extraction endpoint (`app/routers/v1/extract_route.py`)
```
POST /v1/extract
{
  "text": "Full name: Amina Kofi. Date of birth: 1990-03-15. ID: GH-12345",
  "schema": {
    "type": "object",
    "properties": {
      "full_name": { "type": "string" },
      "date_of_birth": { "type": "string", "format": "date" },
      "id_number": { "type": "string" }
    },
    "required": ["full_name", "id_number"]
  },
  "provider": "anthropic"
}
```

#### Step 2 — Use provider-native structured output
- **Anthropic**: pass JSON schema in `tools` as a single `extract_data` tool and force `tool_choice`
- **OpenAI**: use `response_format={"type": "json_schema", "json_schema": {...}}`
- **Groq**: use `response_format={"type": "json_object"}` with schema in system prompt
- **Ollama**: JSON mode + schema in system prompt

#### Step 3 — Validate and return
Run `jsonschema.validate()` on the LLM output. If validation fails, retry once with the error as feedback. Return `{ data: {...}, valid: bool, errors: [...] }`.

**Effort**: ~2 days

---

### ✅ DONE — 6. Conversation History / Session Management

**What the proposal says**: session-aware conversational interfaces

**What to build**: Per-session message history stored in Redis so users can have multi-turn conversations without resending the full history.

**Implementation walkthrough**:

#### Step 1 — Session service (`app/services/session.py`)
```python
async def get_history(session_id: str) -> list[dict]: ...
async def append(session_id: str, role: str, content: str) -> None: ...
async def clear(session_id: str) -> None: ...
```

Keys: `session:{session_id}:messages` (Redis list, capped at `chat.history_limit`).

#### Step 2 — Update chat route
Accept optional `session_id` in `ChatRequest`. If provided, prepend stored history to `messages` before calling `chat_service.chat()`, then append the new exchange.

#### Step 3 — Session lifecycle endpoints
```
DELETE /v1/ai/session/{session_id}    # clear history
GET    /v1/ai/session/{session_id}    # inspect history (admin only)
```

**Effort**: ~1 day  
**Dependencies**: Redis must be enabled

---

### 7. DPI Integration Examples

**What the proposal says**: "at least one example DPI integration"

**Three reference integrations to build** (each as a standalone example in `examples/`):

#### Example A: Social Protection — Voice Enrollment (`examples/social_protection/`)
End-to-end flow:
1. Citizen calls an IVR → audio file received
2. `POST /v1/stt/transcribe` (Intron, local language)
3. `POST /v1/translate` → English
4. `POST /v1/extract` with eligibility schema (name, ID, income declaration)
5. `POST /v1/hitl/review` if confidence < threshold
6. Integration client code showing how to wire these calls together

#### Example B: Health — Clinical Note Summarisation (`examples/health/`)
1. Doctor uploads handwritten note image
2. `POST /v1/documents/ingest` (OCR backend: tesseract or llm)
3. `POST /v1/ai` with RAG — "summarise this patient's conditions and medications"
4. Returns structured FHIR-like summary

#### Example C: Citizen Service — Multilingual Chatbot (`examples/citizen_chatbot/`)
Thin Python/JS client that:
1. Accepts text or voice input
2. Translates to English (if needed)
3. Calls `/v1/ai` with RAG over government FAQ documents
4. Returns response in the citizen's language via `/v1/translate`
5. Optionally speaks the response via `/v1/tts/synthesize`

**Effort**: ~1 week for all three (mostly integration/glue code, services already exist)

---

### 8. Offline / Low-Bandwidth Support

**What the proposal says**: "operate in low-bandwidth and offline-capable environments"

**What to build**: Configuration profile + Dockerfile that boots a fully self-contained stack using only local models (no external API calls).

**Implementation walkthrough**:

#### Step 1 — `docker-compose.sovereign.yml` (override file)
Already started in `docker-compose.yml` with Weaviate + Ollama. Extend to:
- Disable all cloud provider configs
- Set embedding `provider: "local"` with `all-MiniLM-L6-v2`
- Set LLM `provider: "ollama"` with a quantized model (e.g. `llama3.2:3b-q4_K_M`)
- Set STT to Whisper via Ollama or a local `whisper.cpp` container
- Set OCR to `tesseract` only

#### Step 2 — Model pre-pull script (`scripts/pull_sovereign_models.sh`)
```bash
#!/bin/bash
# Pull required Ollama models
docker exec ai-dpi-ollama ollama pull llama3.2:3b-q4_K_M
docker exec ai-dpi-ollama ollama pull nomic-embed-text   # if using Ollama for embeddings
```

#### Step 3 — Sovereign config profile (`config/sovereign.yaml`)
A complete `default_config.yaml` override for fully offline operation.

**Effort**: ~2 days

---

### 9. Observability & Monitoring

**What the proposal says**: "transparency, auditability, and public accountability"

**What to build**: Structured metrics export and a health/readiness endpoint that reflects the state of all backend dependencies.

**Implementation walkthrough**:

#### Step 1 — Prometheus metrics (`app/middleware/metrics.py`)
Use `prometheus-fastapi-instrumentator`. Expose:
- Request count / latency by endpoint and provider
- LLM token usage (add response metadata to provider calls)
- Vector DB query latency
- OCR processing time

#### Step 2 — Enhanced health endpoint (`app/routers/health.py`)
Current `/health` returns 200. Extend to check all dependencies:
```json
{
  "status": "healthy",
  "checks": {
    "redis": "ok",
    "weaviate": "ok",
    "ollama": "ok | unreachable (non-fatal if cloud providers configured)"
  }
}
```

#### Step 3 — Structured audit log enhancements
Current audit middleware logs requests. Add:
- LLM provider used and model name
- Token counts (input/output) where available
- RAG retrieval scores
- Document ingestion job IDs

**Effort**: ~2 days

---

## Recommended Build Order

```
✅ Done:  Schema-constrained extraction (#5) + Session history (#6)
          → Core chat/RAG experience complete

Week 1:  Agent & tool execution runtime (#1)
         → Enables the agentic DPI use cases

Week 2:  Workflow orchestration (#2) + Human-in-the-loop (#3)
         → Enables the full DPI automation pipeline

Week 3:  Guardrails (#4) + Observability (#9)
         → Production hardening

Week 4:  DPI integration examples (#7) + Offline/sovereign profile (#8)
         → Demo-ready reference implementations
```

---

## Sovereign Deployment Quick-Start

To run the full stack with zero external API dependencies:

```bash
# 1. Copy and edit the config
cp app/default_config.yaml config/sovereign.yaml
# Set: llm.providers.ollama.base_url = http://ollama:11434
# Set: llm.embedding_model.provider = local
# Set: llm.vector_database.provider = weaviate, type = http, http_host = weaviate

# 2. Start the stack
docker compose up -d

# 3. Pull a local LLM (first run only)
docker exec $(docker compose ps -q ollama) ollama pull llama3.2

# 4. Ingest a document
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Authorization: Bearer <token>" \
  -F "file=@my_document.pdf" \
  -F "ocr_backend=tesseract"

# 5. Query it
curl -X POST http://localhost:8000/api/v1/ai \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Summarise the key points"}],"provider":"ollama","model":"llama3.2"}'
```

---

## New API Endpoints Added in This Iteration

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/ingest` | Upload PDF/image/text → OCR → chunk → embed → store |
| `POST` | `/api/v1/documents/ingest/text` | Ingest raw text string directly |
| `POST` | `/api/v1/extract` | Extract structured fields from text using JSON Schema |
| `GET` | `/api/v1/ai/session/{session_id}` | Retrieve session message history (admin) |
| `DELETE` | `/api/v1/ai/session/{session_id}` | Clear session history (admin) |

### Existing endpoints that now support sovereign providers

| Endpoint | New option |
|---|---|
| `POST /api/v1/ai` | `"provider": "ollama"` |
| `POST /api/v1/ai/stream` | `"provider": "ollama"` |
| `POST /api/v1/translate` | `"provider": "ollama"` |
| `POST /api/v1/ai/add_vector_db` | Embedding `provider: "local"` in config |
