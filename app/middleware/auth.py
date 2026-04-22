from typing import Callable

from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.oauth import get_current_user
from app.core.logging import logger


# Paths that bypass authentication entirely
PUBLIC_PATHS = {
    "/health",
    "/healthz",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Thin identity-resolution middleware.

    Delegates all token validation to the existing `get_current_user`
    dependency so there is exactly one place where JWT logic lives.

    On success, populates request.state so AuditMiddleware can log a
    resolved actor without needing to re-parse the token:

        request.state.user_id   – str
        request.state.roles     – list[str]
        request.state.token_jti – str | None

    On failure, returns 401 and short-circuits the request before any
    route handler or AuditMiddleware response logging runs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in PUBLIC_PATHS:
            _set_anonymous(request)
            return await call_next(request)

        raw_token = _extract_token(request)

        if not raw_token:
            logger.warning(
                "auth.missing_token",
                extra={"path": request.url.path, "method": request.method},
            )
            return _unauthorized("Missing authentication token")

        try:
            # Re-use your existing dependency directly — no duplicated logic.
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=raw_token
            )
            claims: dict = await get_current_user(credentials)
        except Exception as exc:
            # get_current_user raises HTTPException on any validation failure.
            # Catch broadly so unexpected errors also produce a clean 401
            # rather than a 500 that leaks internal detail.
            status_code = getattr(exc, "status_code", 401)
            detail = getattr(exc, "detail", "Authentication failed")
            logger.warning(
                "auth.rejected",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "detail": detail,
                },
            )
            return _unauthorized(detail, status_code=status_code)

        # Populate state so AuditMiddleware and route handlers can read
        # identity without touching the token again.
        request.state.user_id = claims.get("sub")
        request.state.roles = claims.get("roles", [])
        request.state.token_jti = claims.get("jti")
        return await call_next(request)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_token(request: Request) -> str | None:
    """Bearer header first, session cookie as fallback."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    return request.cookies.get("session_token")


def _set_anonymous(request: Request) -> None:
    request.state.user_id = None
    request.state.roles = []
    request.state.token_jti = None


def _unauthorized(detail: str, status_code: int = 401) -> Response:
    return Response(
        content=f'{{"detail": "{detail}"}}',
        status_code=status_code,
        headers={
            "Content-Type": "application/json",
            "WWW-Authenticate": "Bearer",
        },
    )