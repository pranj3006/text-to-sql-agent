import asyncio
from dataclasses import dataclass

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
from text_to_sql_agent.app.rag.vector_retriever import (
    SchemaVectorRetriever
)


@dataclass(frozen=True)
class CaseEvaluation:
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
    missing_at_10: set[str]


async def evaluate_case(
    test_case: RetrievalTestCase,
) -> CaseEvaluation:
    retriever = SchemaVectorRetriever()
    documents = await retriever.retrieve(
        query=test_case.question,
        limit=10,
    )

    retrieved_ids = [
        document.document_id for document in documents
    ]

    expected_ids = set(test_case.expected_document_ids)

    missing_at_10 = expected_ids - set(retrieved_ids)

    return CaseEvaluation(
        case_id=test_case.case_id,
        question=test_case.question,
        retrieved_ids=retrieved_ids,
        relevance=dict(test_case.relevance),
        recall_at_3=recall_at_k(
            expected_ids, retrieved_ids, 3
        ),
        recall_at_5=recall_at_k(
            expected_ids, retrieved_ids, 5
        ),
        recall_at_10=recall_at_k(
            expected_ids, retrieved_ids, 10
        ),
        precision_at_5=precision_at_k(
            expected_ids, retrieved_ids, 5
        ),
        mrr_at_10=reciprocal_rank(
            expected_ids, retrieved_ids[:10]
        ),
        ndcg_at_5=ndcg_at_k(
            test_case.relevance, retrieved_ids, 5
        ),
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


def print_report(
    evaluations: list[CaseEvaluation],
) -> None:
    print("\n" + "=" * 112)
    print("SCHEMA RETRIEVAL EVALUATION REPORT")
    print("=" * 112)

    print(
        f"{'ID':<7}"
        f"{'Recall@3':<12}"
        f"{'Recall@5':<12}"
        f"{'Recall@10':<12}"
        f"{'Precision@5':<14}"
        f"{'MRR@10':<12}"
        f"{'nDCG@5':<10}"
    )

    print("-" * 79)

    for result in evaluations:
        print(
            f"{result.case_id:<7}"
            f"{result.recall_at_3:<12.3f}"
            f"{result.recall_at_5:<12.3f}"
            f"{result.recall_at_10:<12.3f}"
            f"{result.precision_at_5:<14.3f}"
            f"{result.mrr_at_10:<12.3f}"
            f"{result.ndcg_at_5:<10.3f}"
        )

    print("-" * 79)

    metric_names = (
        "recall_at_3",
        "recall_at_5",
        "recall_at_10",
        "precision_at_5",
        "mrr_at_10",
        "ndcg_at_5",
    )

    print(
        f"{'AVG':<7}"
        + "".join(
            f"{average(evaluations, metric):<{width}.3f}"
            for metric, width in zip(
                metric_names,
                (12, 12, 12, 14, 12, 10),
            )
        )
    )

    print("\nDETAILED RESULTS")

    for result in evaluations:
        print(f"\n{result.case_id}: {result.question}")
        print("Retrieved documents:")

        for rank, document_id in enumerate(
            result.retrieved_ids,
            start=1,
        ):
            grade = result.relevance.get(document_id, 0)

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
            print("Missing relevant documents:")

            for document_id in sorted(result.missing_at_10):
                grade = result.relevance[document_id]
                print(
                    f"  - {document_id} [GRADE {grade}]"
                )
        else:
            print("Missing relevant documents: None")


async def main() -> None:
    evaluations = []

    for test_case in RETRIEVAL_TEST_CASES:
        evaluation = await evaluate_case(test_case)
        evaluations.append(evaluation)

    print_report(evaluations)


if __name__ == "__main__":
    asyncio.run(main())