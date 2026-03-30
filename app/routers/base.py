from fastapi import APIRouter
from app.routers.v1 import base

router = APIRouter(prefix="/api")

router.include_router(base.router)