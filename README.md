# AI-DPI Middleware

> **Developed and maintained by [Data Science Nigeria](https://datasciencenigeria.org)**

An open, model-agnostic AI middleware layer for **Digital Public Infrastructure (DPI)**. Delivers LLM chat, speech-to-text, text-to-speech, and RAG/vector capabilities through a single secure FastAPI gateway — with plug-and-play provider switching and no vendor lock-in.

---

## Features

| Capability | Providers |
|------------|-----------|
| **LLM Chat** | Anthropic (Claude), OpenAI (GPT-4o), Groq (Llama 3.3), Generic OpenAI-compatible |
| **Speech-to-Text** | Groq Whisper, OpenAI Whisper, Deepgram Nova-3, Spitch, Intron Sahara |
| **Text-to-Speech** | Groq PlayAI/Orpheus, OpenAI, ElevenLabs (32 languages), Spitch, Intron Sahara |
| **RAG / Vector DB** | Weaviate (open-source), Pinecone (managed), Qdrant (open-source + cloud) |
| **Auth** | Local JWT (HS256), OIDC RS256/ES256 (Keycloak, Auth0, Google), Token Introspection |
| **Caching & Rate Limiting** | Redis — per-role limits on every endpoint |
| **Audit** | Structured JSON audit log with trace IDs on all requests |

---

## Project Structure

```
app/
├── main.py                        # App wiring and lifespan
├── config.py                      # YAML config loader
├── default_config.yaml            # All configuration lives here
├── auth/
│   ├── oauth.py                   # JWT validation (local HS256 + OIDC RS256/ES256)
│   └── rbac.py                    # require_roles() FastAPI dependency
├── middleware/
│   ├── auth.py                    # Auth middleware with public path bypass
│   ├── audit.py                   # Structured audit logging
│   ├── logger.py                  # Request/response timing logger
│   └── rate_limit.py              # Redis-backed per-role rate limiting
├── providers/
│   ├── deepgram.py                # Deepgram client factory
│   ├── elevenlabs.py              # ElevenLabs client factory
│   └── intron.py                  # Intron API config (no SDK)
├── routers/
│   ├── health.py                  # GET / (docs page) + GET /health
│   └── v1/
│       ├── auth_route.py          # POST /api/v1/auth/token, GET /api/v1/auth/me
│       ├── chat_route.py          # POST /api/v1/ai, /ai/stream, /ai/add_vector_db
│       ├── stt_route.py           # POST /api/v1/stt/transcribe
│       └── tts_route.py           # POST /api/v1/tts/synthesize
├── schemas/
│   ├── auth.py                    # TokenRequest, TokenResponse
│   ├── ai.py                      # ChatRequest, ChatResponse, EmbeddingRequest
│   └── tts.py                     # TTSRequest with full provider/model/voice validation
├── services/
│   ├── chat/                      # LLM routing + provider implementations
│   ├── stt/
│   │   ├── models/                # Per-provider model registries
│   │   └── providers/             # groq, openai, spitch, deepgram, intron
│   ├── tts/
│   │   ├── models/                # Per-provider model/voice/format registries
│   │   └── providers/             # groq, openai, spitch, elevenlabs, intron
│   ├── vectordb/
│   │   └── providers/             # weaviate, pinecone, qdrant
│   ├── embedding/                 # OpenAI text embeddings
│   └── redis.py                   # Async Redis client
└── handlers/
    ├── lifespan.py                # Startup / shutdown hooks
    └── exception.py               # Global HTTP + validation error handlers
```

---

## Setup

### Prerequisites

- Docker + Docker Compose v2 **or** Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- API keys for the AI providers you intend to use

### 1. Clone

```bash
git clone https://github.com/datasciencenigeria/ai-dpi-middleware.git
cd ai-dpi-middleware
```

### 2. Configure

Edit `app/default_config.yaml`. Replace every `[PLACEHOLDER]` with real values.

**Minimum required — auth block:**

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

**LLM providers (add keys for providers you use):**

```yaml
llm:
  providers:
    anthropic:
      api_key: "sk-ant-..."
      default_model: "claude-sonnet-4-6"
    openai:
      api_key: "sk-..."
      default_model: "gpt-4o"
    groq:
      api_key: "gsk_..."
      default_model: "llama-3.3-70b-versatile"
```

**Speech providers:**

```yaml
speech:
  providers:
    groq:      { api_key: "gsk_..." }
    openai:    { api_key: "sk-..." }
    deepgram:  { api_key: "..." }
    elevenlabs:{ api_key: "..." }
    spitch:    { api_key: "..." }
    intron:
      api_key: "..."
      base_url: "https://api.intron.africa/v1"
```

**Vector database (choose one):**

```yaml
# Weaviate (open-source, runs in Docker)
llm:
  vector_database:
    provider: "weaviate"
    type: "http"
    http_host: "weaviate"   # Docker service name
    http_port: 8080
    grpc_port: 50051
    collection_name: "default_collection"

# Pinecone (managed — no Docker needed)
llm:
  vector_database:
    provider: "pinecone"
    API_KEY: "[PINECONE_API_KEY]"
    collection_name: "my-index"   # pre-created; dim=1536 for text-embedding-3-small

# Qdrant (open-source + managed cloud)
llm:
  vector_database:
    provider: "qdrant"
    type: "http"
    http_host: "qdrant"
    http_port: 6333
    collection_name: "default_collection"
```

### 3. Run with Docker Compose (recommended)

```bash
# Start app + Redis
docker compose up -d

# View logs
docker compose logs -f api

# Rebuild after changes
docker compose down
docker compose build --no-cache
docker compose up -d
```

**If using Weaviate or Qdrant locally**, add the service to `docker-compose.yml`:

```yaml
# Weaviate
weaviate:
  image: semitechnologies/weaviate:latest
  ports: ["8080:8080", "50051:50051"]
  environment:
    AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
    DEFAULT_VECTORIZER_MODULE: "none"

# Qdrant
qdrant:
  image: qdrant/qdrant:latest
  ports: ["6333:6333"]
```

### 4. Run locally (development)

```bash
uv sync
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}

# Get a token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=my-client&password=change-me"
```

Browse the interactive docs at `http://localhost:8000/docs`.

---

## API Reference

### Public endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Documentation landing page |
| `GET` | `/health` | JSON health check |
| `POST` | `/api/v1/auth/token` | Exchange `client_id` + `client_secret` for JWT |

### Protected endpoints (Bearer token required)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/auth/me` | any | Verify token, return identity |
| `POST` | `/api/v1/ai` | `user` | LLM chat with optional RAG context |
| `POST` | `/api/v1/ai/stream` | `admin` | Streaming LLM response (SSE) |
| `POST` | `/api/v1/ai/add_vector_db` | `admin` | Store text embedding in vector DB |
| `POST` | `/api/v1/stt/transcribe` | `user` | Speech → text |
| `POST` | `/api/v1/tts/synthesize` | `user` | Text → speech |

---

## Authentication

### Local JWT

```bash
# Get token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=my-client&password=my-secret"

# Use token
curl http://localhost:8000/api/v1/ai \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"provider":"anthropic"}'
```

### OIDC (Keycloak, Auth0, Google)

Tokens from any OIDC provider are accepted directly — no local exchange needed. Configure an `online` issuer in `default_config.yaml`:

```yaml
auth:
  issuers:
    - issuer: "https://your-idp.example.com"
      type: "online"
      jwks_uri: "https://your-idp.example.com/.well-known/jwks.json"
      audience: "your-api-audience"
      algorithm: "RS256"
```

Roles are read from: `roles` claim, `realm_access.roles` (Keycloak), or `resource_access.<client>.roles`.

---

## RBAC

| Role | Endpoints |
|------|-----------|
| `user` | `/ai`, `/stt/transcribe`, `/tts/synthesize`, `/auth/me` |
| `admin` | All `user` endpoints + `/ai/stream`, `/ai/add_vector_db` |

---

## Provider Matrix

Alphabetical. Only providers integrated into this middleware are listed.

| Provider | LLM / Chat | STT | TTS | Language Coverage |
|----------|------------|-----|-----|-------------------|
| `anthropic` | ✓ Claude Opus 4.7, Sonnet 4.6, Haiku 4.5 | — | — | 100+ languages |
| `deepgram` | — | ✓ Nova-3 (6.84% WER), Nova-2, Enhanced, Base — auto-detect, diarization, keyterm prompting | — | 30+ incl. code-switching (EN, ES, FR, DE, HI, RU, PT, JA, IT, NL) |
| `elevenlabs` | — | — | ✓ eleven_multilingual_v2 (emotionally-aware), eleven_flash_v2_5 (<75ms), eleven_turbo_v2_5, eleven_v3, eleven_monolingual_v1 | 32 languages |
| `groq` | ✓ Llama 4 Scout 17B, Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma2 9B | ✓ whisper-large-v3-turbo, whisper-large-v3, distil-whisper-large-v3-en | ✓ orpheus-v1-english (vocal direction), orpheus-arabic-saudi, playai-tts, playai-tts-arabic | Multilingual |
| `intron` | — | ✓ Sahara v1 — 23 African languages, 500+ accents | ✓ Sahara TTS v1 | sw, ha, yo, ig, am, so, zu, xh, af, wo, ff, en + more |
| `openai` | ✓ GPT-4o, GPT-4o mini, o1, o3-mini | ✓ gpt-4o-transcribe, gpt-4o-mini-transcribe, whisper-1 | ✓ gpt-4o-mini-tts (steerable), tts-1, tts-1-hd | 50+ languages |
| `spitch` | — | ✓ Mansa v1 — African-accent optimised, streaming, diarization | ✓ Legacy (African tonal voices) | yo, ha, ig, sw, am + more; EN; bidirectional translation |

---

## Development

```bash
# Install with dev extras
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*Developed and maintained by [Data Science Nigeria](https://datasciencenigeria.org)*
