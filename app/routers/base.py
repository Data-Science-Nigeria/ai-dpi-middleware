from fastapi import APIRouter
from app.routers.v1 import base
from app.routers import health


router = APIRouter(prefix="/api")

router.include_router(base.router)
router.include_router(health.router)