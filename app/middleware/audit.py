import time
import uuid
import json
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from fastapi import Request, Response

from app.core.logging import logger


# Routes that should never appear in audit logs (health checks, metrics, etc.)
EXCLUDED_PATHS = {"/health", "/healthz", "/metrics", "/favicon.ico", "/api/v1/auth/token"}

# Headers that must never be logged
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _redact_headers(headers: dict) -> dict:
    return {
        k: "[REDACTED]" if k.lower() in SENSITIVE_HEADERS else v
        for k, v in headers.items()
    }


async def _read_body(receive: Callable) -> tuple[bytes, Callable]:
    """
    Consume and buffer the request body so it can be both logged
    and forwarded to the actual route handler.
    """
    body_parts: list[bytes] = []

    async def receive_wrapper() -> Message:
        message = await receive()
        if message["type"] == "http.request":
            body_parts.append(message.get("body", b""))
        return message

    # Drain the stream once to capture the body
    initial = await receive()
    body = initial.get("body", b"")

    # Return a new `receive` callable that replays the body
    async def replay() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    return body, replay


def _safe_json(raw: bytes, max_bytes: int = 4096) -> dict | str | None:
    """Parse body as JSON for structured logging; fall back to truncated string."""
    if not raw:
        return None
    if len(raw) > max_bytes:
        return f"<body truncated, {len(raw)} bytes>"
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode("utf-8", errors="replace")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Structured audit middleware.

    Emits one log entry per request containing:
      - Unique trace ID (injected into response headers for correlation)
      - Actor identity pulled from request.state (set by your auth middleware)
      - HTTP method, path, query string
      - Redacted request headers
      - Request body (JSON-parsed when possible, truncated when large)
      - Response status code and size
      - Wall-clock duration in milliseconds
      - Client IP (respects X-Forwarded-For for proxied deployments)

    Usage
    -----
    Add after your authentication middleware so `request.state.user` is
    already populated by the time AuditMiddleware runs:

        app.add_middleware(AuthMiddleware)   # runs second (inner)
        app.add_middleware(AuditMiddleware)  # runs first  (outer)

    The auth middleware should set:
        request.state.user_id  – str | None
        request.state.roles    – list[str] | None
    """

    def __init__(self, app, log_request_body: bool = True):
        super().__init__(app)
        self.log_request_body = log_request_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip noise paths entirely
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id

        # ── Buffer request body ──────────────────────────────────────────────
        body_bytes = b""
        if self.log_request_body and request.method in {"POST", "PUT", "PATCH"}:
            body_bytes, request._receive = await _read_body(request.receive)

        # ── Resolve client IP ────────────────────────────────────────────────
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )

        # ── Resolve actor (populated by upstream auth middleware) ────────────
        user_id: str = getattr(request.state, "user_id", None) or "anonymous"
        roles: list = getattr(request.state, "roles", None) or []

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("audit.request.error | " + json.dumps({
                "trace_id": trace_id,
                "actor": {"user_id": user_id, "roles": roles},
                "http": {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": client_ip,
                    "headers": _redact_headers(dict(request.headers)),
                },
                "request_body": _safe_json(body_bytes),
                "duration_ms": round(duration_ms, 2),
                "error": str(exc),
            }))
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # ── Emit structured audit record ─────────────────────────────────────
        logger.info("audit.request | " + json.dumps({
            "trace_id": trace_id,
            "actor": {"user_id": user_id, "roles": roles},
            "http": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "status_code": response.status_code,
                "client_ip": client_ip,
                "headers": _redact_headers(dict(request.headers)),
                "response_size_bytes": int(response.headers.get("content-length", 0)),
            },
            "request_body": _safe_json(body_bytes) if self.log_request_body else None,
            "duration_ms": round(duration_ms, 2),
        }))

        # Propagate trace ID so callers can correlate logs to a specific request
        response.headers["X-Trace-Id"] = trace_id
        return response