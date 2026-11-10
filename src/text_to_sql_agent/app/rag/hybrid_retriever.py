
import asyncio

from text_to_sql_agent.app.rag.rrf import (
    RRFResult,
    reciprocal_rank_fusion,
)
from text_to_sql_agent.app.rag.schema_retriever import (
    retrieve_schema_documents,
)
from text_to_sql_agent.app.rag.vector_retriever import (
    SchemaVectorRetriever,
)


class SchemaHybridRetriever:
    """Retrieve schema documents using FTS and vector search with RRF."""

    def __init__(
        self,
        vector_retriever: SchemaVectorRetriever | None = None,
    ) -> None:
        self.vector_retriever = (
            vector_retriever or SchemaVectorRetriever()
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        candidate_limit: int = 10,
        k: int = 60,
    ) -> list[RRFResult]:
        """
        Retrieve and fuse FTS and vector search results.

        Args:
            query: Natural-language search query.
            limit: Maximum number of final fused results.
            candidate_limit: Maximum candidates fetched from each retriever.
            k: RRF smoothing constant.

        Returns:
            Fused schema documents ordered by descending RRF score.
        """

        if not query or not query.strip():
            raise ValueError("query cannot be empty.")

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        if candidate_limit < 1:
            raise ValueError(
                "candidate_limit must be greater than zero."
            )

        if k < 0:
            raise ValueError(
                "k must be greater than or equal to zero."
            )

        # Execute independent retrieval operations concurrently.
        fts_results, vector_results = await asyncio.gather(
            retrieve_schema_documents(
                query=query,
                limit=candidate_limit,
            ),
            self.vector_retriever.retrieve(
                query=query,
                limit=candidate_limit,
            ),
        )

        # Fuse the ranked results.
        return reciprocal_rank_fusion(
            fts_results=fts_results,
            vector_results=vector_results,
            k=k,
            limit=limit,
        )
