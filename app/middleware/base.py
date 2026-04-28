from fastapi import FastAPI

from app.middleware.audit import AuditMiddleware
from app.middleware.auth import AuthMiddleware
from app.middleware.logger import LogMiddleware

def add_middleware(app: FastAPI):
    app.add_middleware(LogMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(AuthMiddleware)


    return app