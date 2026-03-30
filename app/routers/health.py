from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "AI-powered Digital Public Infrastructure middleware layer.",
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "endpoints": {
            "POST /api/v1/auth/token": "Exchange client credentials for a JWT",
            "GET  /api/v1/auth/oauth2/login": "Start OAuth2 Authorization Code flow",
            "GET  /api/v1/auth/oauth2/callback": "OAuth2 callback — exchange code for token",
            "POST /api/v1/auth/oauth2/token": "Client credentials via external provider",
            "POST /api/v1/ai/chat": "AI chat (role: user or admin)",
            "POST /api/v1/ai/chat/stream": "Streaming AI chat (role: admin)",
            "GET  /health": "Service health check",
        },
    }


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}