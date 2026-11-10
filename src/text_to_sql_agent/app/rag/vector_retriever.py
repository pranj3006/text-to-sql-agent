from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from text_to_sql_agent.app.db.session import engine
from text_to_sql_agent.app.embeddings.openai_provider import (
    OpenAIEmbeddingProvider,
)
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument

VECTOR_SEARCH_QUERY = text("""
    SELECT
        document_id,
        category,
        title,
        content,
        1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
    FROM public.schema_documents
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:query_embedding AS vector)
    LIMIT :limit
""")


class SchemaVectorRetriever:
    """Retrieve schema documents using vector similarity."""

    def __init__(
        self,
        embedding_provider: OpenAIEmbeddingProvider | None = None,
    ) -> None:
        self.embedding_provider = (
            embedding_provider or OpenAIEmbeddingProvider()
        )

    async def retrieve(
        self,        
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        if not query.strip():
            raise ValueError("query cannot be empty.")

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        query_embedding = await self.embedding_provider.embed_text(
            query
        )
        async with engine.connect() as connection:
            result = await connection.execute(
                VECTOR_SEARCH_QUERY,
                {
                    "query_embedding": str(query_embedding),
                    "limit": limit,
                },
            )


        # return [
        #     {
        #         "document_id": row.document_id,
        #         "category": row.category,
        #         "title": row.title,
        #         "content": row.content,
        #         "similarity": float(row.similarity),
        #     }
        #     for row in result
        # ]

            rows = result.mappings().all()

        return [
            SchemaDocument(
                document_id=row["document_id"],
                category=row["category"],
                title=row["title"],
                content=row["content"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]
