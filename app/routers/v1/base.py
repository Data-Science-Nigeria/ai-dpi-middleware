from fastapi import APIRouter
from app.routers.v1 import (
    auth_route,
    chat_route,
    document_route,
    embedding_route,
    extract_route,
    stt_route,
    translate_route,
    tts_route,
)

router = APIRouter(prefix="/v1")

router.include_router(auth_route.router)
router.include_router(tts_route.router)
router.include_router(stt_route.router)
router.include_router(chat_route.router)
router.include_router(embedding_route.router)
router.include_router(translate_route.router)
router.include_router(document_route.router)
router.include_router(extract_route.router)
