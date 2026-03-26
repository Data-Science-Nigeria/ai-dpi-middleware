from fastapi import APIRouter
from app.routers.v1 import (
    ai_route,
    auth_route
)

router = APIRouter(prefix="/v1")

router.include_router(auth_route.router)
router.include_router(ai_route.router)