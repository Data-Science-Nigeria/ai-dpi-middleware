import time

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from app.core.logging import logger


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request details
        logger.info(f"Request: {request.method} {request.url.components.path}")

        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        # Log response details with process time
        logger.info(
            f"Request: {request.method} {request.url.components.path} Response Status: {response.status_code}, Process Time: {process_time:.2f} ms"
        )

        return response
