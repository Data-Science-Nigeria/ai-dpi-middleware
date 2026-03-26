# AI DPI Middleware

An async FastAPI middleware layer for **Digital Public Infrastructure (DPI)** that exposes AI capabilities through a secure, role-based API. Supports local JWT authentication, OIDC/OAuth2 via any standards-compliant provider (Keycloak, Google, Auth0), and Redis-backed state management.

---

## Features

- **Async FastAPI** with versioned routes (`/api/v1/...`)
- **Dual auth strategies** — local HS256 JWT or external OIDC RS256/ES256 tokens
- **OAuth2 flows** — Authorization Code (browser login) and Client Credentials (M2M)
- **Role-based access control (RBAC)** on all protected routes
- **Anthropic AI** integration with streaming support
- **Redis** for OAuth2 state management (CSRF protection)
- **Docker + Docker Compose** ready

---

## Project Structure

```
app/
├── main.py                   # App wiring
├── config.py                 # All settings via .env (pydantic-settings)
├── handlers/
│   ├── lifespan.py           # Startup / shutdown (AI + Redis warmup)
│   └── exception.py          # Global HTTP, validation, and 500 handlers
├── auth/
│   ├── oauth.py              # JWT validation (HS256 local / RS256 OIDC)
│   └── rbac.py               # require_roles() FastAPI dependency
├── routers/
│   ├── health.py             # GET /  and  GET /health
│   ├── base.py               # Mounts health + v1
│   └── v1/
│       ├── auth_route.py     # POST /api/v1/auth/token
│       ├── oauth2_route.py   # OAuth2 Authorization Code + Client Credentials
│       └── ai_route.py       # POST /api/v1/ai/chat  +  /chat/stream
├── schemas/
│   ├── auth.py               # TokenRequest, TokenResponse
│   ├── ai.py                 # Message, ChatRequest, ChatResponse
│   └── oauth.py              # OAuth2 request/response models
├── services/
│   ├── ai.py                 # Async Anthropic client
│   └── redis.py              # Async Redis client
└── middleware/
    ├── base.py               # Middleware registration
    └── logger.py             # Request/response logging with timing
```

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd ai-dpi-middleware
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Minimum required fields:

```bash
CLIENTS={"myapp":{"secret":"change-me","roles":["user"]}}
JWT_SECRET=<openssl rand -hex 32>
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

### 4. Run locally

```bash
# Redis must be running
uv run uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

---

## API Reference

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service description and endpoint map |
| `GET` | `/health` | Health check |

### Auth — `/api/v1/auth`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/token` | Exchange `client_id` + `client_secret` for a local JWT |

### OAuth2 — `/api/v1/auth/oauth2`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/auth/oauth2/login` | Redirect to external provider (Authorization Code flow) |
| `GET` | `/api/v1/auth/oauth2/callback` | Receive code, exchange for provider tokens |
| `POST` | `/api/v1/auth/oauth2/token` | Client credentials via external provider (M2M) |

### AI — `/api/v1/ai` *(Bearer token required)*

| Method | Endpoint | Role required | Description |
|--------|----------|---------------|-------------|
| `POST` | `/api/v1/ai/chat` | `user` or `admin` | Send messages, get AI response |
| `POST` | `/api/v1/ai/chat/stream` | `admin` | Streaming AI response |

---

## Authentication

### Local JWT (client credentials)

```bash
# 1. Get a token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "myapp", "client_secret": "change-me"}'

# 2. Use the token
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

### OIDC (external provider token)

Tokens issued by any OIDC provider (Keycloak, Google, Auth0) are accepted directly — no local token exchange needed. Set `OIDC_JWKS_URI` in `.env` and pass the provider's `id_token` as the Bearer token.

---

## OIDC Provider Setup

### Keycloak

```bash
OIDC_ISSUER=https://{host}/realms/{realm}
OIDC_JWKS_URI=https://{host}/realms/{realm}/protocol/openid-connect/certs
OIDC_AUDIENCE=account

OAUTH2_CLIENT_ID=ai-dpi-middleware
OAUTH2_CLIENT_SECRET=<from Keycloak client credentials tab>
OAUTH2_AUTHORIZATION_ENDPOINT=https://{host}/realms/{realm}/protocol/openid-connect/auth
OAUTH2_TOKEN_ENDPOINT=https://{host}/realms/{realm}/protocol/openid-connect/token
OAUTH2_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth2/callback
OAUTH2_SCOPES=["openid","profile","email","roles"]
```

### Google

```bash
OIDC_JWKS_URI=https://www.googleapis.com/oauth2/v3/certs
OIDC_AUDIENCE=<your-google-client-id>

OAUTH2_CLIENT_ID=<your-google-client-id>
OAUTH2_CLIENT_SECRET=<your-google-client-secret>
OAUTH2_AUTHORIZATION_ENDPOINT=https://accounts.google.com/o/oauth2/v2/auth
OAUTH2_TOKEN_ENDPOINT=https://oauth2.googleapis.com/token
OAUTH2_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth2/callback
OAUTH2_SCOPES=["openid","profile","email"]
```

---

## RBAC — Roles

| Role | Access |
|------|--------|
| `user` | `POST /ai/chat` |
| `admin` | `POST /ai/chat` + `POST /ai/chat/stream` |

Roles are embedded in the JWT at token issuance. Configure them per client in `CLIENTS`:

```bash
CLIENTS={"myapp":{"secret":"s3cr3t","roles":["user"]},"admin-app":{"secret":"s3cr3t","roles":["admin","user"]}}
```

For OIDC tokens, roles are read from:
- `roles` claim (local / standard)
- `realm_access.roles` (Keycloak realm roles)
- `resource_access.<client>.roles` (Keycloak client roles)

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLIENTS` | Yes | `{}` | JSON client registry |
| `JWT_SECRET` | Yes | — | HS256 signing secret |
| `JWT_EXPIRE_MINUTES` | No | `60` | Token lifetime |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Model to use |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `OIDC_JWKS_URI` | No | — | Enables OIDC token validation |
| `OIDC_AUDIENCE` | No | — | Expected `aud` claim |
| `OAUTH2_*` | No | — | Enables OAuth2 flows |
| `CORS_ORIGINS` | No | `["*"]` | Allowed CORS origins |

---

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint
uv run ruff check .
```
