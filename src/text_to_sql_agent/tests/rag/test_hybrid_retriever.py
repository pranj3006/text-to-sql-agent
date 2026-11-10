import asyncio
from unittest.mock import AsyncMock

import pytest

from text_to_sql_agent.app.rag import hybrid_retriever
from text_to_sql_agent.app.rag.hybrid_retriever import (
    SchemaHybridRetriever,
)
from text_to_sql_agent.app.rag.rrf import RRFResult
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument


def make_document(document_id: str) -> SchemaDocument:
    return SchemaDocument(
        document_id=document_id,
        category="table",
        title=f"{document_id} table",
        content=f"Content for {document_id}",
    )


def test_hybrid_retriever_invokes_both_retrievers(monkeypatch):
    async def run_test():
        fts_results = [
            make_document("table_customers"),
            make_document("table_orders"),
        ]

        vector_results = [
            make_document("table_orders"),
            make_document("table_customers"),
        ]

        fts_mock = AsyncMock(return_value=fts_results)

        vector_retriever = SchemaVectorRetrieverMock(
            return_value=vector_results
        )

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            fts_mock,
        )

        retriever = SchemaHybridRetriever(
            vector_retriever=vector_retriever
        )

        results = await retriever.retrieve(
            query="customer revenue",
            limit=5,
            candidate_limit=10,
        )

        fts_mock.assert_awaited_once_with(
            query="customer revenue",
            limit=10,
        )

        vector_retriever.retrieve.assert_awaited_once_with(
            query="customer revenue",
            limit=10,
        )

        assert len(results) == 2
        assert all(isinstance(result, RRFResult) for result in results)

    asyncio.run(run_test())


def test_hybrid_retriever_fuses_results_correctly(monkeypatch):
    async def run_test():
        fts_results = [
            make_document("table_customers"),
            make_document("table_orders"),
        ]

        vector_results = [
            make_document("table_orders"),
            make_document("table_customers"),
        ]

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            AsyncMock(return_value=fts_results),
        )

        vector_retriever = SchemaVectorRetrieverMock(
            return_value=vector_results
        )

        retriever = SchemaHybridRetriever(vector_retriever)

        results = await retriever.retrieve(
            query="customer revenue",
            limit=5,
        )

        by_id = {
            result.document.document_id: result
            for result in results
        }

        customers = by_id["table_customers"]

        assert customers.fts_rank == 1
        assert customers.vector_rank == 2
        assert customers.rrf_score == pytest.approx(
            1 / 61 + 1 / 62
        )

        orders = by_id["table_orders"]

        assert orders.fts_rank == 2
        assert orders.vector_rank == 1

    asyncio.run(run_test())


def test_hybrid_retriever_respects_final_limit(monkeypatch):
    async def run_test():
        fts_results = [
            make_document("table_customers"),
            make_document("table_orders"),
            make_document("table_products"),
        ]

        vector_results = [
            make_document("table_products"),
            make_document("table_orders"),
            make_document("table_customers"),
        ]

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            AsyncMock(return_value=fts_results),
        )

        retriever = SchemaHybridRetriever(
            SchemaVectorRetrieverMock(return_value=vector_results)
        )

        results = await retriever.retrieve(
            query="sales analysis",
            limit=2,
            candidate_limit=3,
        )

        assert len(results) == 2

    asyncio.run(run_test())


def test_hybrid_retriever_executes_retrievers_concurrently(monkeypatch):
    async def run_test():
        both_started = asyncio.Event()
        started_count = 0

        async def fake_fts(query: str, limit: int):
            nonlocal started_count
            started_count += 1

            if started_count == 2:
                both_started.set()

            await asyncio.wait_for(both_started.wait(), timeout=2)

            return [make_document("table_customers")]

        class ConcurrentVectorRetriever:
            async def retrieve(self, query: str, limit: int):
                nonlocal started_count
                started_count += 1

                if started_count == 2:
                    both_started.set()

                await asyncio.wait_for(both_started.wait(), timeout=2)

                return [make_document("table_orders")]

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            fake_fts,
        )

        retriever = SchemaHybridRetriever(
            vector_retriever=ConcurrentVectorRetriever()
        )

        results = await retriever.retrieve(
            query="customer orders",
            candidate_limit=5,
        )

        assert started_count == 2
        assert len(results) == 2

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "kwargs, expected_message",
    [
        ({"query": ""}, "query cannot be empty"),
        ({"query": "   "}, "query cannot be empty"),
        ({"query": "customers", "limit": 0}, "limit must be greater"),
        (
            {"query": "customers", "candidate_limit": 0},
            "candidate_limit must be greater",
        ),
        (
            {"query": "customers", "k": -1},
            "k must be greater than or equal to zero",
        ),
    ],
)
def test_hybrid_retriever_validates_inputs(
    monkeypatch,
    kwargs,
    expected_message,
):
    async def run_test():
        fts_mock = AsyncMock()
        vector_retriever = SchemaVectorRetrieverMock()

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            fts_mock,
        )

        retriever = SchemaHybridRetriever(vector_retriever)

        with pytest.raises(ValueError, match=expected_message):
            await retriever.retrieve(**kwargs)

        # Invalid inputs must be rejected before database/API calls.
        fts_mock.assert_not_awaited()
        vector_retriever.retrieve.assert_not_awaited()

    asyncio.run(run_test())


def test_hybrid_retriever_propagates_fts_exception(monkeypatch):
    async def run_test():
        async def failing_fts(query: str, limit: int):
            raise RuntimeError("FTS retrieval failed")

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            failing_fts,
        )

        retriever = SchemaHybridRetriever(
            SchemaVectorRetrieverMock()
        )

        with pytest.raises(
            RuntimeError,
            match="FTS retrieval failed",
        ):
            await retriever.retrieve("customer revenue")

    asyncio.run(run_test())


def test_hybrid_retriever_propagates_vector_exception(monkeypatch):
    async def run_test():
        class FailingVectorRetriever:
            async def retrieve(self, query: str, limit: int):
                raise RuntimeError("Vector retrieval failed")

        monkeypatch.setattr(
            hybrid_retriever,
            "retrieve_schema_documents",
            AsyncMock(return_value=[]),
        )

        retriever = SchemaHybridRetriever(
            FailingVectorRetriever()
        )

        with pytest.raises(
            RuntimeError,
            match="Vector retrieval failed",
        ):
            await retriever.retrieve("customer revenue")

    asyncio.run(run_test())


class SchemaVectorRetrieverMock:
    """Mock vector retriever for hybrid retrieval tests."""

    def __init__(self, return_value=None):
        self.return_value = return_value or []
        self.retrieve = AsyncMock(return_value=self.return_value)