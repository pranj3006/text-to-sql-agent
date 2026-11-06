"""
AuthContextMiddleware: best-effort, non-enforcing identity resolution.

Design note: actual auth/RBAC ENFORCEMENT is done via FastAPI route
dependencies (`Depends(get_current_user)`, `Depends(require_roles(...))`)
rather than global middleware, because different routes need different
rules (some are public, some need a role, some need record-level checks)
and dependencies compose per-router far more cleanly than a single
middleware trying to special-case every path.

What THIS middleware does is cheap and purely additive: if a bearer token
is present and valid, it populates the `user_id` logging contextvar (see
RequestContextMiddleware) so access logs show *who* made the request even
on routes where auth is optional. It never rejects a request - a missing
or invalid token here just leaves the request unauthenticated, and any
route that actually requires auth still enforces it via its dependency.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger, user_id_ctx
from app.core.security import validate_token
from app.services.cache_service import get_cache_service

logger = get_logger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                cache = get_cache_service()
                claims = await validate_token(token, cache)
                user_id_ctx.set(claims.get("oid") or claims.get("sub") or "unknown")
            except Exception:
                # Swallow - enforcement (and the real 401) happens in the route dependency.
                logger.debug("auth_context_token_not_validated")
        return await call_next(request)
