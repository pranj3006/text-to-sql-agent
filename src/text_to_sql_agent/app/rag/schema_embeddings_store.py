import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from text_to_sql_agent.app.db.session import AsyncSessionLocal
from text_to_sql_agent.app.embeddings.openai_provider import (
    OpenAIEmbeddingProvider,
)
from text_to_sql_agent.app.rag.schema_documents import get_schema_documents
import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine

UPDATE_EMBEDDING = text("""
    UPDATE public.schema_documents
    SET embedding = CAST(:embedding AS vector)
    WHERE document_id = :document_id
""")


BATCH_SIZE = 50


async def index_schema_embeddings( 
    engine: AsyncEngine) -> None:
    documents = get_schema_documents()

    if not documents:
        print("No schema documents found.")
        return

    provider = OpenAIEmbeddingProvider()

    total_indexed = 0

    async with AsyncSessionLocal() as session:
        try:
            for start in range(0, len(documents), BATCH_SIZE):
                batch = documents[start:start + BATCH_SIZE]

                texts = [
                    f"{document.title}\n{document.content}"
                    for document in batch
                ]

                embeddings = await provider.embed_texts(texts)

                if len(embeddings) != len(batch):
                    raise RuntimeError(
                        "Embedding count does not match document count."
                    )

                for document, embedding in zip(
                    batch,
                    embeddings,
                    strict=True,
                ):
                    await session.execute(
                        UPDATE_EMBEDDING,
                        {
                            "document_id": document.document_id,
                            "embedding": str(embedding),
                        },
                    )

                await session.commit()

                total_indexed += len(batch)

                print(
                    f"Indexed {total_indexed}/{len(documents)} "
                    "schema document embeddings."
                )

        except Exception:
            await session.rollback()
            raise

    print(
        f"Successfully indexed embeddings for "
        f"{total_indexed} schema documents."
    )
    return total_indexed
