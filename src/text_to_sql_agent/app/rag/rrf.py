
from dataclasses import dataclass

from text_to_sql_agent.app.rag.schema_documents import SchemaDocument


@dataclass(frozen=True)
class RRFResult:
    """A schema document with reciprocal rank fusion metadata."""

    document: SchemaDocument
    fts_rank: int | None
    vector_rank: int | None
    rrf_score: float


def reciprocal_rank_fusion(
    fts_results: list[SchemaDocument],
    vector_results: list[SchemaDocument],
    *,
    k: int = 60,
    limit: int = 10,
) -> list[RRFResult]:
    """
    Combine FTS and vector retrieval results using Reciprocal Rank Fusion.

    Ranking is based on the position of each document in the input lists,
    not on the original FTS or vector scores.

    Args:
        fts_results: Documents ordered by FTS relevance.
        vector_results: Documents ordered by vector relevance.
        k: RRF smoothing constant.
        limit: Maximum number of fused results to return.

    Returns:
        Documents ordered by descending RRF score.

    Notes:
        - Ranks are 1-based.
        - Duplicate document IDs within a retriever count only once.
        - FTS metadata takes precedence if the same document ID has
          different document objects in both result lists.
        - Equal scores are ordered by document_id for determinism.
    """

    if k < 0:
        raise ValueError("k must be greater than or equal to zero.")

    if limit < 1:
        raise ValueError("limit must be greater than zero.")

    # document_id -> fusion metadata
    fused_documents: dict[str, dict] = {}

    def add_results(
        results: list[SchemaDocument],
        retriever: str,
    ) -> None:
        seen_document_ids: set[str] = set()

        for rank, document in enumerate(results, start=1):
            document_id = document.document_id

            # Count only the first occurrence from each retriever.
            if document_id in seen_document_ids:
                continue

            seen_document_ids.add(document_id)

            if document_id not in fused_documents:
                fused_documents[document_id] = {
                    "document": document,
                    "fts_rank": None,
                    "vector_rank": None,
                    "rrf_score": 0.0,
                }

            entry = fused_documents[document_id]

            entry[f"{retriever}_rank"] = rank
            entry["rrf_score"] += 1.0 / (k + rank)

    # Process FTS first so its document metadata is canonical
    # if duplicate IDs contain different document objects.
    add_results(fts_results, "fts")
    add_results(vector_results, "vector")

    fused_results = [
        RRFResult(
            document=entry["document"],
            fts_rank=entry["fts_rank"],
            vector_rank=entry["vector_rank"],
            rrf_score=entry["rrf_score"],
        )
        for entry in fused_documents.values()
    ]

    # Higher RRF scores indicate better combined relevance.
    # document_id provides deterministic tie-breaking.
    fused_results.sort(
        key=lambda result: (
            -result.rrf_score,
            result.document.document_id,
        )
    )

    return fused_results[:limit]
