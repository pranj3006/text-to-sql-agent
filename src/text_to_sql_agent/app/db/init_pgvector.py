"""
Ensures the pgvector extension exists. Called once at startup (main.py
lifespan) - also mirrored in the first Alembic migration so fresh envs
provisioned purely via `alembic upgrade head` get it too.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from text_to_sql_agent.app.core.logging import get_logger

logger = get_logger(__name__)


async def ensure_pgvector_extension(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    logger.info("pgvector_extension_ready")
