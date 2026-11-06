"""
Central caching service - the ONLY place in the app that talks to the
cache Redis DB directly. Every other module calls CacheService methods
so cache-key conventions, serialization, and TTL defaults stay
consistent, and so the backing store can be swapped later without
touching call sites.

Also provides a `cached()` decorator for the common "cache the return
value of this async function" pattern used in services.
"""
import functools
import hashlib
import json
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.core.logging import get_logger
from text_to_sql_agent.app.core.redis_client import get_redis_cache_pool

logger = get_logger(__name__)


class CacheService:
    def __init__(self):
        self._redis = get_redis_cache_pool()

    @staticmethod
    def build_key(*parts: str) -> str:
        return ":".join([settings.APP_NAME, *[str(p) for p in parts]])

    async def get_json(self, key: str) -> Any | None:
        raw = await self._redis.get(key)
        return json.loads(raw) if raw is not None else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl or settings.CACHE_DEFAULT_TTL_SECONDS)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def delete_by_prefix(self, prefix: str) -> None:
        """Use sparingly (SCAN-based) - fine for admin/cache-bust operations, not hot paths."""
        async for key in self._redis.scan_iter(match=f"{prefix}*"):
            await self._redis.delete(key)

    async def get_or_set(
        self, key: str, factory: Callable[[], Awaitable[Any]], ttl: int | None = None
    ) -> Any:
        cached = await self.get_json(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set_json(key, value, ttl=ttl)
        return value

    # --- simple distributed lock, useful around cache-stampede-prone rebuilds ---
    async def acquire_lock(self, name: str, ttl_seconds: int = 30) -> bool:
        return bool(await self._redis.set(f"lock:{name}", "1", nx=True, ex=ttl_seconds))

    async def release_lock(self, name: str) -> None:
        await self._redis.delete(f"lock:{name}")


@lru_cache
def _cache_singleton() -> CacheService:
    return CacheService()


def get_cache_service() -> CacheService:
    """FastAPI dependency AND plain callable (e.g. from middleware) - both work."""
    return _cache_singleton()


def cached(key_prefix: str, ttl: int | None = None):
    """
    Decorator for async functions: caches by key_prefix + hash of args/kwargs.
    Usage:
        @cached("rag:embedding", ttl=3600)
        async def embed_text(text: str) -> list[float]: ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_service()
            arg_hash = hashlib.sha256(json.dumps([args, kwargs], default=str).encode()).hexdigest()[:16]
            key = cache.build_key(key_prefix, arg_hash)
            cached_value = await cache.get_json(key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await cache.set_json(key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
