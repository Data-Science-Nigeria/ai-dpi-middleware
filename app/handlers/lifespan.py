"""Application startup and shutdown handlers."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import get_config
from app.core.logging import logger
from app.services import redis as redis_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = get_config()

    # Ensure data directories declared in the YAML config exist
    for folder in (
        cfg['document']['pdf_folder'],
        cfg['document']['image_folder'],
        cfg['document']['audio_folder'],
    ):
        Path(folder).mkdir(parents=True, exist_ok=True)

    if cfg['redis']['enabled']:
        logger.info("Initializing Redis connection...")
        redis_service.get_client()  # warm up Redis connection
    yield
    if cfg['redis']['enabled']:
        logger.info("Closing Redis connection...")
        await redis_service.close()
