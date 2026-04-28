"""Issue JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.config import get_config
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

_jwt_cfg = get_config().get('jwt', {})  # type: ignore
_clients_cfg = get_config().get('clients', {})  # type: ignore

@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Exchange client credentials for a JWT containing the client's roles."""
    client = _clients_cfg.get(body.client_id, None)

    if not client or client.secret != body.client_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = client.roles
    expires_in = _jwt_cfg.get('expire_minutes') * 60
    payload = {
        "sub": body.client_id,
        "roles": roles,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_jwt_cfg.get('expire_minutes', 15)),
    }
    token = jwt.encode(payload, _jwt_cfg.get('secret', ''), algorithm=_jwt_cfg.get('algorithm', 'HS256'))
    return TokenResponse(access_token=token, expires_in=expires_in, roles=roles)
