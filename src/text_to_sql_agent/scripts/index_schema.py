
import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine


async def main(
    engine: AsyncEngine,
    indexer: Callable[[AsyncEngine], Awaitable[int]],
) -> None:
    try:
        count = await indexer(engine)
        print(f"Indexed {count} schema documents.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    from text_to_sql_agent.app.db.session import engine
    from text_to_sql_agent.app.rag.schema_store import index_schema_documents

    asyncio.run(main(engine, index_schema_documents))
