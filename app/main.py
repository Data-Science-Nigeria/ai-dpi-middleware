"""Application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.handlers.exception import add_exception_handlers
from app.handlers.lifespan import lifespan
from app.middleware.base import add_middleware
from app.routers import base, health

_cfg = get_config()
_app_cfg = _cfg.get('app', {})  # type: ignore
_cors_cfg = _cfg.get('cors', {})  # type: ignore

app = FastAPI(
    title=_app_cfg.get('name', "AI DPI Middleware"),
    version=_app_cfg.get('version', "0.1.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_cfg.get('allow_origins', []),
    allow_credentials=_cors_cfg.get('allow_credentials', False),
    allow_methods=_cors_cfg.get('allow_methods', []),
    allow_headers=_cors_cfg.get('allow_headers', []),
)

add_middleware(app)
add_exception_handlers(app)

app.include_router(base.router)
app.include_router(health.router)

