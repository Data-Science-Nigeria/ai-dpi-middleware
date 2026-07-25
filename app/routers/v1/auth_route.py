"""Issue JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt

from app.auth.oauth import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.auth import TokenResponse
from app.auth.oauth import  _auth_cfgs

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/token",
    responses={
        400: {"description": "No local auth provider configured; token could not be generated."},
        401: {"description": "Invalid client credentials."},
    },
)
async def issue_token(body: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """Exchange client credentials for a JWT containing the client's roles."""    
    for cfg in _auth_cfgs:
        if cfg.get("type", "") == "local":
            client = cfg.get(body.username, None)
            
            if client is None or client['secret'] != body.password:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

            roles = client['roles']
            expires_in = cfg.get('expire_minutes') * 60
            payload = {
                "sub": str(body.client_id),
                "roles": roles,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in),
            }
            token = jwt.encode(claims = payload, 
                            key =cfg.get("key", ""), 
                            algorithm=cfg.get('algorithm', 'HS256'))
            return TokenResponse(access_token=token, expires_in=expires_in, roles=roles)

    raise HTTPException(detail="Error Generating token", status_code=400)


@router.get("/me")
async def verify_me(user: Annotated[dict, Depends(get_current_user)]):
    return user

@router.get("/protected_route")
async def protected_route(user: Annotated[dict, Depends(get_current_user)]):
    return {"message": "User can acess the protected route."}

