
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from text_to_sql_agent.app.rag.schema_documents import get_schema_documents


UPSERT_DOCUMENT = text("""
    INSERT INTO schema_documents (
        document_id,
        category,
        title,
        content,
        updated_at
    )
    VALUES (
        :document_id,
        :category,
        :title,
        :content,
        NOW()
    )
    ON CONFLICT (document_id)
    DO UPDATE SET
        category = EXCLUDED.category,
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        updated_at = NOW()
""")


async def index_schema_documents(engine: AsyncEngine) -> int:
    documents = get_schema_documents()

    payload = [
        {
            "document_id": doc.document_id,
            "category": doc.category,
            "title": doc.title,
            "content": doc.content,
        }
        for doc in documents
    ]

    async with engine.begin() as connection:
        await connection.execute(UPSERT_DOCUMENT, payload)

    return len(payload)