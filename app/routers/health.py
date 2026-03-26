from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "AI-powered Digital Public Infrastructure middleware layer."
    }


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}