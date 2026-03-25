"""OAuth2 JWT bearer token validation.

Fetches the JWKS from the configured issuer and validates incoming
Bearer tokens on every protected request.  Works with any standards-
compliant OAuth2/OIDC provider (Keycloak, Auth0, Google, etc.).
"""

from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import settings

bearer_scheme = HTTPBearer()

# Simple in-process JWKS cache (refreshed on decode failure).
_jwks_cache: dict | None = None


async def _fetch_jwks() -> dict:
    global _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.jwks_uri, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


async def _get_jwks() -> dict:
    if _jwks_cache is None:
        return await _fetch_jwks()
    return _jwks_cache


def _find_key(jwks: dict, kid: str | None) -> dict | None:
    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return key
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Dependency that validates the Bearer JWT and returns its claims."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise credentials_exception

    kid = unverified_header.get("kid")
    jwks = await _get_jwks()
    key_data = _find_key(jwks, kid)

    if key_data is None:
        # Stale cache — try a fresh fetch once
        jwks = await _fetch_jwks()
        key_data = _find_key(jwks, kid)

    if key_data is None:
        raise credentials_exception

    try:
        public_key = jwk.construct(key_data)
        options = {"verify_aud": bool(settings.oauth_audience)}
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[unverified_header.get("alg", "RS256")],
            audience=settings.oauth_audience or None,
            options=options,
        )
    except JWTError:
        raise credentials_exception

    return payload