from fastapi import FastAPI

from app.middleware.logger import LogMiddleware

def add_middleware(app: FastAPI):
    app.add_middleware(LogMiddleware)

    return app