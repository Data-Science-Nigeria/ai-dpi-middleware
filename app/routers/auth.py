"""Issue JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from jose import jwt
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Exchange client credentials for a JWT."""
    if body.client_id != settings.client_id or body.client_secret != settings.client_secret:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": body.client_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return TokenResponse(access_token=token, expires_in=expires_in)
