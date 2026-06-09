"""Prometheus request instrumentation middleware."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics import active_requests, request_latency, requests_total

_SKIP = frozenset(["/metrics", "/health", "/"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP:
            return await call_next(request)

        active_requests.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            elapsed = time.perf_counter() - start
            endpoint = request.url.path
            method = request.method
            request_latency.labels(method=method, endpoint=endpoint).observe(elapsed)
            requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()
            active_requests.dec()

        return response
