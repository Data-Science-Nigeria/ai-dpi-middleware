"""Application startup and shutdown handlers."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config_yaml import get_yaml_config
from app.core.logging import logger
from app.services import redis as redis_service
from app.services.ai import get_client as get_ai_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = get_yaml_config()

    # Ensure data directories declared in the YAML config exist
    for folder in (
        cfg.document.pdf_folder,
        cfg.document.image_folder,
        cfg.document.audio_folder,
    ):
        Path(folder).mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Config loaded — llm.backend={cfg.llm.backend}, "
        f"rag.top_k={cfg.rag.top_k}, "
        f"security.rate_limits.global_default={cfg.security.rate_limits.global_default}"
    )

    get_ai_client()             # warm up Anthropic client
    redis_service.get_client()  # warm up Redis connection
    yield
    await redis_service.close()
