"""Request logging middleware — records method, path, status, duration (no bodies: may hold PII)."""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("nova.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path,
                    response.status_code, duration_ms)
        return response
