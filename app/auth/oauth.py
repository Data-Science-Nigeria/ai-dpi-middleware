"""JWT bearer token validation.

Supports two strategies, selected automatically by the token's `alg` header:

- HS256  → local token issued by POST /v1/auth/token
- RS256 / ES256  → external OIDC token validated against the provider's JWKS
"""

from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

from app.config import settings

bearer_scheme = HTTPBearer()

_LOCAL_ALGORITHMS = {"HS256", "HS384", "HS512"}
_OIDC_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}

# In-process JWKS cache — refreshed automatically on key-not-found
_jwks_cache: dict | None = None


async def _fetch_jwks() -> dict:
    global _jwks_cache
    if not settings.oidc_jwks_uri:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC is not configured on this server",
        )
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.oidc_jwks_uri, timeout=10)
        resp.raise_for_status()
        data: dict = resp.json()
    _jwks_cache = data
    return data


async def _get_jwks() -> dict:
    if _jwks_cache is None:
        return await _fetch_jwks()
    return _jwks_cache


def _find_key(jwks: dict, kid: str | None) -> dict | None:
    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return key
    return None


async def _validate_local(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty token payload")
    return payload


async def _validate_oidc(token: str, alg: str, kid: str | None) -> dict:
    jwks = await _get_jwks()
    key_data = _find_key(jwks, kid)

    if key_data is None:
        # Stale cache — refresh once
        jwks = await _fetch_jwks()
        key_data = _find_key(jwks, kid)

    if key_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signing key not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        public_key = jwk.construct(key_data)
        options = {"verify_aud": bool(settings.oidc_audience)}
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            audience=settings.oidc_audience or None,
            options=options,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OIDC token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty token payload")
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token: str = credentials.credentials
    """Validate a Bearer JWT and return its claims.

    Routes to local HS256 validation or OIDC JWKS validation based on the
    token's `alg` header field.
    """

    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not parse token header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    alg: str = header.get("alg", "")
    kid: str | None = header.get("kid")

    if alg in _LOCAL_ALGORITHMS:
        return await _validate_local(token)

    if alg in _OIDC_ALGORITHMS:
        return await _validate_oidc(token, alg, kid)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unsupported token algorithm: {alg}",
        headers={"WWW-Authenticate": "Bearer"},
    )
