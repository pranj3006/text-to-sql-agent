
import pytest

from text_to_sql_agent.app.rag.rrf import (
    RRFResult,
    reciprocal_rank_fusion,
)
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument


def make_document(document_id: str) -> SchemaDocument:
    """Create a minimal schema document for testing."""
    return SchemaDocument(
        document_id=document_id,
        category="table",
        title=f"{document_id} table",
        content=f"Content for {document_id}",
    )


def test_fuses_documents_from_both_retrievers():
    """Documents returned by both retrievers should combine their ranks."""

    fts_results = [
        make_document("table_customers"),
        make_document("table_orders"),
    ]

    vector_results = [
        make_document("table_orders"),
        make_document("table_customers"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        vector_results,
        k=60,
    )

    assert len(results) == 2

    # Both documents have identical combined scores.
    assert results[0].document.document_id == "table_customers"
    assert results[1].document.document_id == "table_orders"

    customers = results[0]
    assert customers.fts_rank == 1
    assert customers.vector_rank == 2
    assert customers.rrf_score == pytest.approx(
        1 / 61 + 1 / 62
    )

    orders = results[1]
    assert orders.fts_rank == 2
    assert orders.vector_rank == 1
    assert orders.rrf_score == pytest.approx(
        1 / 62 + 1 / 61
    )


def test_document_present_only_in_fts():
    fts_results = [
        make_document("table_customers"),
        make_document("table_orders"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        [],
    )

    assert len(results) == 2

    customers = next(
        result for result in results
        if result.document.document_id == "table_customers"
    )

    assert customers.fts_rank == 1
    assert customers.vector_rank is None
    assert customers.rrf_score == pytest.approx(1 / 61)


def test_document_present_only_in_vector():
    vector_results = [
        make_document("table_products"),
        make_document("table_orders"),
    ]

    results = reciprocal_rank_fusion(
        [],
        vector_results,
    )

    assert len(results) == 2

    products = results[0]

    assert products.document.document_id == "table_products"
    assert products.fts_rank is None
    assert products.vector_rank == 1
    assert products.rrf_score == pytest.approx(1 / 61)


def test_duplicate_document_ids_are_counted_once_per_retriever():
    document = make_document("table_customers")

    fts_results = [
        document,
        make_document("table_customers"),
    ]

    vector_results = [
        make_document("table_customers"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        vector_results,
    )

    assert len(results) == 1

    result = results[0]

    # First occurrence in FTS is rank 1.
    # Duplicate FTS occurrence must not contribute.
    assert result.fts_rank == 1
    assert result.vector_rank == 1
    assert result.rrf_score == pytest.approx(
        1 / 61 + 1 / 61
    )


def test_preserves_original_ranks():
    fts_results = [
        make_document("table_customers"),
        make_document("table_orders"),
        make_document("table_products"),
    ]

    vector_results = [
        make_document("table_products"),
        make_document("table_customers"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        vector_results,
    )

    by_id = {
        result.document.document_id: result
        for result in results
    }

    assert by_id["table_customers"].fts_rank == 1
    assert by_id["table_customers"].vector_rank == 2

    assert by_id["table_orders"].fts_rank == 2
    assert by_id["table_orders"].vector_rank is None

    assert by_id["table_products"].fts_rank == 3
    assert by_id["table_products"].vector_rank == 1


def test_equal_scores_are_sorted_by_document_id():
    fts_results = [
        make_document("table_orders"),
        make_document("table_customers"),
    ]

    vector_results = [
        make_document("table_customers"),
        make_document("table_orders"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        vector_results,
    )

    document_ids = [
        result.document.document_id
        for result in results
    ]

    assert document_ids == [
        "table_customers",
        "table_orders",
    ]


def test_respects_result_limit():
    fts_results = [
        make_document("table_customers"),
        make_document("table_orders"),
        make_document("table_products"),
    ]

    results = reciprocal_rank_fusion(
        fts_results,
        [],
        limit=2,
    )

    assert len(results) == 2


def test_empty_inputs_return_empty_results():
    results = reciprocal_rank_fusion(
        [],
        [],
    )

    assert results == []


@pytest.mark.parametrize("k", [-1, -10])
def test_rejects_negative_k(k):
    with pytest.raises(ValueError, match="k must be"):
        reciprocal_rank_fusion([], [], k=k)


@pytest.mark.parametrize("limit", [0, -1])
def test_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit must be"):
        reciprocal_rank_fusion([], [], limit=limit)
