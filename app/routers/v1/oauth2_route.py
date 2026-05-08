"""OAuth2 flows: Authorization Code and Client Credentials."""

from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.config import get_config
from app.schemas.oauth import OAuth2ClientCredentialsRequest, OAuth2TokenResponse
from app.services.redis import get_client as get_redis

router = APIRouter(prefix="/auth/oauth2", tags=["OAuth2"])

_STATE_PREFIX = "oauth2:state:"

_oauth2_cfg = get_config().get('oauth2_config', {})  # type: ignore

def _require_oauth2_config() -> None:
    missing = [
        field
        for field, value in {
            "oauth2_client_id": _oauth2_cfg['client_id'],
            "oauth2_client_secret": _oauth2_cfg('client_secret'),
            "oauth2_authorization_endpoint": _oauth2_cfg.get('auth_endpoint', ""),
            "oauth2_token_endpoint": _oauth2_cfg.get('token_endpoint', ""),
            "oauth2_redirect_uri": _oauth2_cfg.get('redirect_uri', ""),
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth2 not fully configured. Missing: {missing}",
        )


# ---------------------------------------------------------------------------
# Authorization Code Flow
# ---------------------------------------------------------------------------
@router.get("/login")
async def oauth2_login() -> RedirectResponse:
    """Redirect the user to the external OAuth2 provider's authorization page."""
    _require_oauth2_config()

    state = secrets.token_urlsafe(32)
    redis = get_redis()
    await redis.setex(f"{_STATE_PREFIX}{state}", _oauth2_cfg('state_ttl_seconds'), "1")

    scope = " ".join(_oauth2_cfg('scopes'))
    params = (
        f"?response_type=code"
        f"&client_id={_oauth2_cfg('client_id')}"
        f"&redirect_uri={_oauth2_cfg('redirect_uri')}"
        f"&scope={scope}"
        f"&state={state}"
    )
    return RedirectResponse(url=f"{_oauth2_cfg('authorization_endpoint')}{params}")


@router.get("/callback", response_model=OAuth2TokenResponse)
async def oauth2_callback(
    code: str = Query(...),
    state: str | None = Query(None),
) -> OAuth2TokenResponse:
    """Receive the authorization code, validate state, and exchange for tokens."""
    _require_oauth2_config()

    if state:
        redis = get_redis()
        key = f"{_STATE_PREFIX}{state}"
        valid = await redis.getdel(key)  # atomic get-and-delete
        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth2 state")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _oauth2_cfg('token_endpoint'),  # type: ignore[arg-type]
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _oauth2_cfg('redirect_uri'),
                "client_id": _oauth2_cfg('client_id'),
                "client_secret": _oauth2_cfg('client_secret'),
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token exchange failed: {resp.text}",
        )

    data = resp.json()
    return OAuth2TokenResponse(
        access_token=data["access_token"],
        token_type=data.get("token_type", "bearer"),
        expires_in=data.get("expires_in"),
        id_token=data.get("id_token"),
        scope=data.get("scope"),
    )


# ---------------------------------------------------------------------------
# Client Credentials Flow (machine-to-machine via external provider)
# ---------------------------------------------------------------------------

@router.post("/token", response_model=OAuth2TokenResponse)
async def oauth2_client_credentials(body: OAuth2ClientCredentialsRequest) -> OAuth2TokenResponse:
    """Obtain a token from the external provider using client credentials."""
    if not _oauth2_cfg('token_endpoint'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="oauth2_token_endpoint is not configured",
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _oauth2_cfg('token_endpoint'),
            data={
                "grant_type": "client_credentials",
                "client_id": body.client_id,
                "client_secret": body.client_secret,
                "scope": body.scope or " ".join(_oauth2_cfg('scopes')),
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Client credentials rejected: {resp.text}",
        )

    data = resp.json()
    return OAuth2TokenResponse(
        access_token=data["access_token"],
        token_type=data.get("token_type", "bearer"),
        expires_in=data.get("expires_in"),
        scope=data.get("scope"),
    )
