"""Issue JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.config import get_config
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

_oauth2_cfg = get_config().get('oauth2_config', {})
_clients_cfg = _oauth2_cfg.get("client_credentials", {})

@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Exchange client credentials for a JWT containing the client's roles."""
    client = _clients_cfg.get(body.client_id, None)
    print(client['secret'])

    if client is None or client['secret'] != body.client_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = client['roles']
    expires_in = _oauth2_cfg.get('jwt_expire_minutes') * 60
    payload = {
        "sub": body.client_id,
        "roles": roles,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in),
    }
    token = jwt.encode(claims = payload, 
                       key =_oauth2_cfg.get("jwt_secret_key", ""), 
                       algorithm=_oauth2_cfg.get('algorithm', 'HS256'))
    return TokenResponse(access_token=token, expires_in=expires_in, roles=roles)
