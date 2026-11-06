"""
Single place that owns Redis connection pools. Three logical usages share
the same Redis instance but different logical DBs so they can be reasoned
about / flushed independently in dev:

  DB 0 - general cache            (settings.REDIS_DB_CACHE)
  DB 1 - celery broker            (settings.REDIS_DB_CELERY_BROKER)
  DB 2 - celery result backend    (settings.REDIS_DB_CELERY_BACKEND)
  DB 3 - pub/sub for websockets   (settings.REDIS_DB_PUBSUB)

Everything else in the app should import get_redis_cache_pool /
get_redis_pubsub_pool rather than constructing redis.Redis() ad hoc.
"""
from functools import lru_cache

import redis.asyncio as aioredis

from text_to_sql_agent.app.core.config import settings


@lru_cache
def get_redis_cache_pool() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url_cache,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )


@lru_cache
def get_redis_pubsub_pool() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url_pubsub,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )


async def close_redis_pools() -> None:
    await get_redis_cache_pool().aclose()
    await get_redis_pubsub_pool().aclose()
