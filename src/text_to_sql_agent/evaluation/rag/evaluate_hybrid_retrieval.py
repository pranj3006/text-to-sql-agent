
import asyncio
import time

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from text_to_sql_agent.app.rag.schema_retriever import (
    retrieve_schema_documents,
)
from text_to_sql_agent.app.rag.vector_retriever import (
    SchemaVectorRetriever,
)
from text_to_sql_agent.app.rag.hybrid_retriever import (
    SchemaHybridRetriever,
)
from text_to_sql_agent.evaluation.rag.retrieval_cases import (
    RETRIEVAL_TEST_CASES,
    RetrievalTestCase,
)
from text_to_sql_agent.evaluation.rag.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


DEFAULT_RETRIEVAL_LIMIT = 10
DEFAULT_HYBRID_CANDIDATE_LIMIT = 10


@dataclass(frozen=True)
class CaseEvaluation:
    strategy: str
    case_id: str
    question: str
    retrieved_ids: list[str]
    relevance: dict[str, int]
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    precision_at_5: float
    mrr_at_10: float
    ndcg_at_5: float
    latency_ms: float
    missing_at_10: set[str]


RetrieverFunction = Callable[
    [str, int],
    Awaitable[list[str]],
]


async def evaluate_case(
    test_case: RetrievalTestCase,
    strategy: str,
    retrieve: RetrieverFunction,
) -> CaseEvaluation:
    """Execute one retrieval strategy for one evaluation case."""

    start_time = time.perf_counter()

    retrieved_ids = await retrieve(
        test_case.question,
        DEFAULT_RETRIEVAL_LIMIT,
    )

    latency_ms = (
        time.perf_counter() - start_time
    ) * 1000

    expected_ids = set(test_case.expected_document_ids)

    missing_at_10 = expected_ids - set(retrieved_ids[:10])

    return CaseEvaluation(
        strategy=strategy,
        case_id=test_case.case_id,
        question=test_case.question,
        retrieved_ids=retrieved_ids,
        relevance=dict(test_case.relevance),
        recall_at_3=recall_at_k(
            expected_ids,
            retrieved_ids,
            3,
        ),
        recall_at_5=recall_at_k(
            expected_ids,
            retrieved_ids,
            5,
        ),
        recall_at_10=recall_at_k(
            expected_ids,
            retrieved_ids,
            10,
        ),
        precision_at_5=precision_at_k(
            expected_ids,
            retrieved_ids,
            5,
        ),
        mrr_at_10=reciprocal_rank(
            expected_ids,
            retrieved_ids[:10],
        ),
        ndcg_at_5=ndcg_at_k(
            test_case.relevance,
            retrieved_ids,
            5,
        ),
        latency_ms=latency_ms,
        missing_at_10=missing_at_10,
    )


def average(
    evaluations: list[CaseEvaluation],
    metric_name: str,
) -> float:
    if not evaluations:
        return 0.0

    return sum(
        getattr(evaluation, metric_name)
        for evaluation in evaluations
    ) / len(evaluations)


def print_comparison_report(
    evaluations: list[CaseEvaluation],
) -> None:
    """Print aggregate metrics for all retrieval strategies."""

    strategies = ["FTS", "Vector", "Hybrid RRF"]

    metric_columns = (
        ("recall_at_3", "Recall@3"),
        ("recall_at_5", "Recall@5"),
        ("recall_at_10", "Recall@10"),
        ("precision_at_5", "Precision@5"),
        ("mrr_at_10", "MRR@10"),
        ("ndcg_at_5", "nDCG@5"),
        ("latency_ms", "Latency(ms)"),
    )

    print("\n" + "=" * 125)
    print("SCHEMA RETRIEVAL COMPARISON REPORT")
    print("=" * 125)

    header = f"{'Strategy':<15}"

    for _, label in metric_columns:
        header += f"{label:<15}"

    print(header)
    print("-" * 125)

    for strategy in strategies:
        strategy_results = [
            evaluation
            for evaluation in evaluations
            if evaluation.strategy == strategy
        ]

        if not strategy_results:
            continue

        row = f"{strategy:<15}"

        for metric_name, _ in metric_columns:
            value = average(
                strategy_results,
                metric_name,
            )

            row += f"{value:<15.3f}"

        print(row)

    print("=" * 125)


def print_detailed_results(
    evaluations: list[CaseEvaluation],
) -> None:
    """Print per-question retrieval rankings and metrics."""

    strategies = ["FTS", "Vector", "Hybrid RRF"]

    for strategy in strategies:
        strategy_results = [
            evaluation
            for evaluation in evaluations
            if evaluation.strategy == strategy
        ]

        print("\n" + "=" * 110)
        print(f"DETAILED RESULTS: {strategy}")
        print("=" * 110)

        for result in strategy_results:
            print(f"\n{result.case_id}: {result.question}")

            print(
                f"Latency: {result.latency_ms:.2f} ms"
            )

            print(
                f"Recall@3: {result.recall_at_3:.3f} | "
                f"Recall@5: {result.recall_at_5:.3f} | "
                f"Recall@10: {result.recall_at_10:.3f} | "
                f"Precision@5: {result.precision_at_5:.3f} | "
                f"MRR@10: {result.mrr_at_10:.3f} | "
                f"nDCG@5: {result.ndcg_at_5:.3f}"
            )

            print("\nRetrieved documents:")

            for rank, document_id in enumerate(
                result.retrieved_ids,
                start=1,
            ):
                grade = result.relevance.get(
                    document_id,
                    0,
                )

                if grade == 2:
                    label = "ESSENTIAL"
                elif grade == 1:
                    label = "USEFUL"
                else:
                    label = "IRRELEVANT"

                print(
                    f"  {rank:>2}. {document_id} [{label}]"
                )

            if result.missing_at_10:
                print("\nMissing relevant documents:")

                for document_id in sorted(
                    result.missing_at_10
                ):
                    grade = result.relevance[document_id]

                    print(
                        f"  - {document_id} [GRADE {grade}]"
                    )
            else:
                print("\nMissing relevant documents: None")


async def main() -> None:
    evaluations: list[CaseEvaluation] = []

    # Initialize retrievers once and reuse them.
    vector_retriever = SchemaVectorRetriever()

    hybrid_retriever = SchemaHybridRetriever(
        vector_retriever=vector_retriever
    )

    # Strategy 1: FTS
    async def retrieve_fts(
        query: str,
        limit: int,
    ) -> list[str]:
        documents = await retrieve_schema_documents(
            query=query,
            limit=limit,
        )

        return [
            document.document_id
            for document in documents
        ]

    # Strategy 2: Vector
    async def retrieve_vector(
        query: str,
        limit: int,
    ) -> list[str]:
        documents = await vector_retriever.retrieve(
            query=query,
            limit=limit,
        )

        return [
            document.document_id
            for document in documents
        ]

    # Strategy 3: Hybrid RRF
    async def retrieve_hybrid(
        query: str,
        limit: int,
    ) -> list[str]:
        results = await hybrid_retriever.retrieve(
            query=query,
            limit=limit,
            candidate_limit=DEFAULT_HYBRID_CANDIDATE_LIMIT,
        )

        return [
            result.document.document_id
            for result in results
        ]

    strategies: dict[str, RetrieverFunction] = {
        "FTS": retrieve_fts,
        "Vector": retrieve_vector,
        "Hybrid RRF": retrieve_hybrid,
    }

    # Run strategies sequentially to avoid unnecessary
    # cross-strategy database and embedding contention.
    for strategy_name, retrieve in strategies.items():
        print(f"\nRunning strategy: {strategy_name}")

        for test_case in RETRIEVAL_TEST_CASES:
            evaluation = await evaluate_case(
                test_case=test_case,
                strategy=strategy_name,
                retrieve=retrieve,
            )

            evaluations.append(evaluation)

            print(
                f"  {evaluation.case_id}: "
                f"nDCG@5={evaluation.ndcg_at_5:.3f}, "
                f"Recall@3={evaluation.recall_at_3:.3f}, "
                f"Latency={evaluation.latency_ms:.2f} ms"
            )

    print_comparison_report(evaluations)
    print_detailed_results(evaluations)


if __name__ == "__main__":
    asyncio.run(main())
