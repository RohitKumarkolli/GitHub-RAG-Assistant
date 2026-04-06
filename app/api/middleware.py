# app/api/middleware.py

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]   

        request.state.request_id = request_id

        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"REQUEST  | {request.method:<6} {request.url.path:<40} "
                f"| 500 | {elapsed_ms:8.1f}ms | req={request_id} | "
                f"UNHANDLED: {exc}"
            )
            raise

        elapsed_ms = (time.time() - start_time) * 1000

        status = response.status_code
        status_indicator = (
            "✅" if status < 300 else
            "⚠️ " if status < 500 else
            "❌"
        )

        logger.info(
            f"REQUEST  | {request.method:<6} {str(request.url.path):<40} "
            f"| {status} {status_indicator} | {elapsed_ms:8.1f}ms | "
            f"req={request_id}"
        )

        response.headers["X-Request-ID"]      = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["X-XSS-Protection"]       = "1; mode=block"
        return response