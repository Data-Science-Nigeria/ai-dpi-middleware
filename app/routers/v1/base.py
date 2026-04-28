from fastapi import APIRouter
from app.routers.v1 import ai_route, auth_route, oauth2_route, stt_route, tts_route

router = APIRouter(prefix="/v1")

router.include_router(auth_route.router)
router.include_router(oauth2_route.router)
router.include_router(ai_route.router)
router.include_router(tts_route.router)
router.include_router(stt_route.router)