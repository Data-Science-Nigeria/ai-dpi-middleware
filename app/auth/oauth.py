from __future__ import annotations

import time
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.config import get_config

_auth_cfgs = get_config().get("auth", [])

bearer_scheme = HTTPBearer()

# -----------------------------
# JWKS CACHE (fixed + TTL)
# -----------------------------
_jwks_cache: dict[str, tuple[float, dict]] = {}  # jwk_uri -> (timestamp, data)
JWKS_TTL = 300  # 5 minutes

_http_client = httpx.AsyncClient(timeout=10)


# -----------------------------
# JWKS FETCH WITH CACHE
# -----------------------------
async def _fetch_jwks(jwk_uri: str) -> dict:
    now = time.time()

    cached = _jwks_cache.get(jwk_uri)
    if cached:
        ts, data = cached
        if now - ts < JWKS_TTL:
            return data

    try:
        resp = await _http_client.get(jwk_uri)
        resp.raise_for_status()
        data = resp.json()

        _jwks_cache[jwk_uri] = (now, data)
        return data

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch JWKS"
        )


# -----------------------------
# INTROSPECTION
# -----------------------------
async def _validate_introspection(token: str, cfg: dict) -> dict:
    url = cfg.get("introspect_api")
    client_id = cfg.get("client_id")
    client_secret = cfg.get("client_secret")

    if not url or not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Introspection not configured"
        )

    data = {
        "token": token,
        "client_id": client_id,
        "client_secret": client_secret
    }

    try:
        resp = await _http_client.post(url, data=data)
        resp.raise_for_status()
        result = resp.json()

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Introspection request failed"
        )

    if not result.get("active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive token"
        )

    return result


# -----------------------------
# LOCAL JWT (HS256)
# -----------------------------
async def _validate_hs256(token: str, cfg: dict) -> dict:
    try:
        return jwt.decode(
            token,
            cfg["key"],
            algorithms=[cfg["algorithm"]],
            audience=cfg.get("audience"),
            issuer=cfg.get("issuer"),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid local token"
        )


# -----------------------------
# OIDC JWKS VALIDATION
# -----------------------------
async def _validate_jwks(token: str, cfg: dict) -> dict:
    jwk_uri = cfg.get("jwks_uri")
    algorithm = cfg.get("algorithm")
    audience = cfg.get("audience")
    issuer = cfg.get("issuer")

    if not jwk_uri or not algorithm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC not configured"
        )

    jwks = await _fetch_jwks(jwk_uri)

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    if not kid:
        raise HTTPException(
            status_code=401,
            detail="Missing kid"
        )

    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)

    if not key:
        raise HTTPException(
            status_code=401,
            detail="Signing key not found"
        )

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# -----------------------------
# CORE AUTH ROUTER (SAFE)
# -----------------------------
async def _validate_with_provider(token: str, cfg: dict) -> dict:
    if cfg.get("jwks_uri"):
        return await _validate_jwks(token, cfg)

    if cfg.get("introspect_api"):
        return await _validate_introspection(token, cfg)

    if cfg.get("key"):
        return await _validate_hs256(token, cfg)

    raise HTTPException(
        status_code=401,
        detail="Invalid auth provider configuration"
    )


# -----------------------------
# MAIN DEPENDENCY
# -----------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:

    token = credentials.credentials

    for cfg in _auth_cfgs:
        try:
            return await _validate_with_provider(token, cfg)
        except HTTPException as _:
            continue

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed"
    )