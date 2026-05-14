"""Issue JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt

from app.auth.oauth import get_current_user
from app.config import get_config
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

_oauth2_cfg = get_config().get('auth', {})
_clients_cfg = _oauth2_cfg.get("client_credentials", {})

@router.post("/token")
async def issue_token(body: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """Exchange client credentials for a JWT containing the client's roles."""
    print(body)
    client = _clients_cfg.get(body.username, None)
    print(client['secret'])

    if client is None or client['secret'] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = client['roles']
    expires_in = _clients_cfg.get('jwt_expire_minutes') * 60
    payload = {
        "sub": body.client_id,
        "roles": roles,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in),
    }
    token = jwt.encode(claims = payload, 
                       key =_oauth2_cfg.get("jwt_secret_key", ""), 
                       algorithm=_oauth2_cfg.get('algorithm', 'HS256'))
    return TokenResponse(access_token=token, expires_in=expires_in, roles=roles)


@router.get("/me")
async def verify_me(user: dict = Depends(get_current_user)):
    return user

@router.get("/protected_route")
async def protected_route(user: dict = Depends(get_current_user)):
    return {"message": "User can acess the protected route."}

