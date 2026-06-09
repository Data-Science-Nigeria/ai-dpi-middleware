# AI-DPI Middleware

> **Developed and maintained by [Data Science Nigeria](https://datasciencenigeria.org)**

An open, model-agnostic AI middleware layer for **Digital Public Infrastructure (DPI)**. Delivers LLM chat, RAG document intelligence, speech, translation, and structured extraction through a single secure FastAPI gateway — with plug-and-play provider switching and no vendor lock-in.

---

## Features

| Capability                        | Providers                                                                               |
| --------------------------------- | --------------------------------------------------------------------------------------- |
| **LLM Chat + Streaming**    | Anthropic, OpenAI, Groq, Gemini, Generic OpenAI-compatible,**Ollama (sovereign)** |
| **RAG Ingestion**           | PDF, DOCX, PPTX, XLSX, CSV, RTF, ODT, TXT, MD — OCR for scanned docs                   |
| **Structured Extraction**   | JSON Schema-constrained field extraction, provider-native structured output             |
| **Translation**             | LLM-backed, 100+ languages including African low-resource languages                     |
| **Speech-to-Text**          | Groq Whisper, OpenAI Whisper, Deepgram Nova-3, Spitch, Intron Sahara                    |
| **Text-to-Speech**          | Groq PlayAI/Orpheus, OpenAI, ElevenLabs, Spitch, Intron Sahara                          |
| **Embeddings**              | OpenAI (cloud), sentence-transformers**(sovereign, no API key)**                  |
| **Vector DB**               | Weaviate (open-source), Qdrant (open-source), Pinecone (managed)                        |
| **Auth**                    | Local JWT (HS256), OIDC RS256/ES256 (Keycloak, Auth0, Google), Token Introspection      |
| **Session History**         | Redis-backed multi-turn conversation history with configurable TTL                      |
| **Caching + Rate Limiting** | Redis — per-role limits on every endpoint                                              |
| **Audit**                   | Structured JSON audit log with trace IDs on all requests                                |

---

## Setup

### Prerequisites

- Docker + Docker Compose v2 **or** Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- API keys for the cloud providers you use (none needed for sovereign/local mode)

### 1. Clone

```bash
git clone https://github.com/datasciencenigeria/ai-dpi-middleware.git
cd ai-dpi-middleware
```

### 2. Configure

Edit `app/default_config.yaml`. Replace every `[PLACEHOLDER]` with real values.

**Minimum — auth:**

```yaml
auth:
  issuers:
    - issuer: "my-service"
      type: "local"
      key: "your-32-byte-hex-secret"   # openssl rand -hex 32
      algorithm: HS256
      expire_minutes: 60
      my-client:
        secret: "change-me"
        roles: ["user"]
      admin-client:
        secret: "change-me-admin"
        roles: ["admin", "user"]
```

**LLM providers:**

```yaml
llm:
  providers:
    anthropic:
      api_key: "sk-ant-..."
    openai:
      api_key: "sk-..."
    groq:
      api_key: "gsk_..."
```

### 3. Run

```bash
# Dev (cloud providers) — starts api + redis only
docker compose up -d

# Sovereign (local models) — adds Weaviate + Ollama
docker compose --profile sovereign up -d

docker compose logs -f api
```

**Local dev:**

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=my-client&password=change-me"
```

Browse interactive docs at `http://localhost:8000/docs`.

---

## Sovereign Deployment (Fully Offline)

Run with zero external API calls — no vendor keys, no data leaving the host.

### Stack

```
Ollama        → local LLM inference (any open-weight model)
Weaviate      → local vector database  (Docker, data on-disk)
sentence-transformers → local embeddings (downloaded once, cached)
Tesseract     → local OCR
```

All four ship in the `docker-compose.yml` already. Just configure:

```yaml
# app/default_config.yaml

llm:
  providers:
    ollama:
      base_url: "http://ollama:11434"
      default_model: "qwen2.5:0.5b"

  embedding_model:
    provider: "local"
    model: "all-MiniLM-L6-v2"       # downloaded once on first use

  vector_database:
    provider: "weaviate"
    type: "http"
    http_host: "weaviate"
```

Then pull a model and start:

```bash
docker compose --profile sovereign up -d

# Pull a model (first time only — ~2 GB)
docker compose exec ollama ollama pull qwen2.5:0.5b

# Chat
curl -X POST http://localhost:8000/api/v1/ai \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"provider":"ollama","model":"qwen2.5:0.5b"}'
```

### Using a custom / fine-tuned model

If you have a GGUF file (fine-tuned on local-language or domain data):

```bash
# 1. Create a Modelfile
cat > Modelfile <<EOF
FROM /models/my-custom-model.gguf
SYSTEM "You are a DPI assistant for Nigerian public services."
PARAMETER temperature 0.9
EOF

# 2. Mount model into container (docker-compose.yml volumes):
#    - ./models:/models

# 3. Register with Ollama
docker compose exec ollama ollama create my-model -f /models/Modelfile

# 4. Use it
curl ... -d '{"provider":"ollama","model":"my-model",...}'
```

Supported input formats: **GGUF** (native). For Hugging Face safetensors, convert with [llama.cpp&#39;s `convert_hf_to_gguf.py`](https://github.com/ggerganov/llama.cpp) first.

### Recommended sovereign models

| Use case                     | Model                   | Size   |
| ---------------------------- | ----------------------- | ------ |
| **Local dev / testing**      | `qwen2.5:0.5b` ★ default | 397 MB |
| General chat                 | `llama3.2`              | 2 GB   |
| Long context / reasoning     | `qwen2.5:7b`            | 4 GB   |
| Multilingual (African langs) | `aya-expanse:8b`        | 5 GB   |
| Low-resource device          | `phi3.5:mini`           | 2 GB   |
| Embeddings                   | `nomic-embed-text`      | 270 MB |

Pull any with `ollama pull <model>`.

---

## RAG — Document Ingestion

```bash
# Ingest a PDF (Tesseract OCR for scanned pages)
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@report.pdf" \
  -F "ocr_backend=tesseract" \
  -F "language=eng"

# Ingest a Word doc
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@policy.docx"

# Ingest raw text
curl -X POST http://localhost:8000/api/v1/documents/ingest/text \
  -H "Authorization: Bearer <admin-token>" \
  -d "text=The eligibility criteria are...&source=policy-manual"
```

**Supported formats:** PDF, DOCX, DOC, PPTX, XLSX, CSV, RTF, ODT, TXT, MD, PNG, JPG, TIFF, BMP, WEBP

**OCR backends:** `tesseract` (local, sovereign) · `llm` (Claude/GPT-4o vision, higher quality)

Chat automatically retrieves relevant context from stored documents — no extra configuration needed.

---

## Structured Extraction

Extract typed fields from free-form text using the LLM's native structured output:

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Full name: Amina Kofi. Date of birth: 1990-03-15. ID: GH-12345.",
    "output_schema": {
      "type": "object",
      "properties": {
        "full_name":     { "type": "string" },
        "date_of_birth": { "type": "string" },
        "id_number":     { "type": "string" }
      },
      "required": ["full_name", "id_number"]
    },
    "provider": "anthropic"
  }'
```

Output is validated against the schema. Failed validation triggers a retry with the error fed back to the LLM.

---

## Session History (Multi-turn Chat)

Pass `session_id` in any chat request to maintain conversation history across calls:

```bash
# Turn 1
curl ... -d '{"session_id":"user-123","messages":[{"role":"user","content":"What is DPI?"}],...}'

# Turn 2 — prior context prepended automatically
curl ... -d '{"session_id":"user-123","messages":[{"role":"user","content":"Give an example."}],...}'
```

Requires `redis.enabled: true` in config. Session TTL and history limit are configurable in the `chat:` block.

---

## API Reference

### Public

| Method   | Path                   | Description  |
| -------- | ---------------------- | ------------ |
| `GET`  | `/health`            | Health check |
| `POST` | `/api/v1/auth/token` | Get JWT      |

### Protected (Bearer token required)

| Method     | Path                              | Role  | Description                 |
| ---------- | --------------------------------- | ----- | --------------------------- |
| `GET`    | `/api/v1/auth/me`               | any   | Verify token                |
| `POST`   | `/api/v1/ai`                    | user  | Chat with RAG context       |
| `POST`   | `/api/v1/ai/stream`             | admin | Streaming chat (SSE)        |
| `POST`   | `/api/v1/extract`               | user  | Structured field extraction |
| `POST`   | `/api/v1/translate`             | user  | Text translation            |
| `POST`   | `/api/v1/stt/transcribe`        | user  | Speech → text              |
| `POST`   | `/api/v1/tts/synthesize`        | user  | Text → speech              |
| `POST`   | `/api/v1/documents/ingest`      | admin | Ingest document into RAG    |
| `POST`   | `/api/v1/documents/ingest/text` | admin | Ingest raw text into RAG    |
| `POST`   | `/api/v1/ai/add_vector_db`      | admin | Embed and store text        |
| `GET`    | `/api/v1/ai/session/{id}`       | admin | Get session history         |
| `DELETE` | `/api/v1/ai/session/{id}`       | admin | Clear session               |

---

## Authentication

### Local JWT

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=my-client&password=my-secret"

curl http://localhost:8000/api/v1/ai \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"provider":"anthropic"}'
```

### OIDC (Keycloak, Auth0, Google)

```yaml
auth:
  issuers:
    - issuer: "https://your-idp.example.com"
      type: "online"
      jwks_uri: "https://your-idp.example.com/.well-known/jwks.json"
      audience: "your-api-audience"
      algorithm: "RS256"
```

Roles read from: `roles` claim, `realm_access.roles` (Keycloak), or `resource_access.<client>.roles`.

---

## Provider Matrix

| Provider             | Chat         | STT | TTS | Notes                                                |
| -------------------- | ------------ | --- | --- | ---------------------------------------------------- |
| `anthropic`        | ✓           | —  | —  | Claude Opus 4.7, Sonnet 4.6, Haiku 4.5               |
| `openai`           | ✓           | ✓  | ✓  | GPT-4o, Whisper, TTS-1/HD                            |
| `groq`             | ✓           | ✓  | ✓  | Llama 4, Whisper, PlayAI/Orpheus                     |
| `gemini`           | ✓           | —  | —  | Gemini 2.5 Flash/Pro                                 |
| `deepgram`         | —           | ✓  | —  | Nova-3, 30+ languages                                |
| `elevenlabs`       | —           | —  | ✓  | 32 languages, <75ms flash model                      |
| `spitch`           | —           | ✓  | ✓  | African-accent optimised                             |
| `intron`           | —           | ✓  | ✓  | 23 African languages, 500+ accents                   |
| **`ollama`** | **✓** | —  | —  | **Sovereign — any GGUF model, fully offline** |

---

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*Developed and maintained by [Data Science Nigeria](https://datasciencenigeria.org)*
