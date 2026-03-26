"""Application startup and shutdown handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.services.ai import get_client as get_ai_client
from app.services import redis as redis_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_ai_client()               # warm up Anthropic client
    redis_service.get_client()    # warm up Redis connection
    yield
    await redis_service.close()   # graceful shutdown
