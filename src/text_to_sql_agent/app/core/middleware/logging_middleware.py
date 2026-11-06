"""
- Assigns/propagates an X-Correlation-Id per request (accepts an inbound
  one so it can be threaded from the frontend / API gateway).
- Logs a single structured access-log line per request with latency and
  status code.
- Populates the correlation_id/user_id contextvars logging.py reads from,
  so every log line emitted while handling this request carries them
  automatically without passing them around explicitly.
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import correlation_id_ctx, get_logger, user_id_ctx

logger = get_logger("app.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
        correlation_id_ctx.set(correlation_id)

        # Set by AuthMiddleware once the token is decoded, defaults to anonymous.
        user_id_ctx.set("anonymous")

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Correlation-Id"] = correlation_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
