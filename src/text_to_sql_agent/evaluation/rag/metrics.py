import math
from collections.abc import Mapping, Sequence


def recall_at_k(
    expected_ids: set[str],
    retrieved_ids: Sequence[str],
    k: int,
) -> float:
    if not expected_ids:
        raise ValueError("Expected document IDs cannot be empty.")

    if k < 1:
        raise ValueError("k must be greater than zero.")

    retrieved = set(retrieved_ids[:k])

    return len(expected_ids.intersection(retrieved)) / len(expected_ids)


def precision_at_k(
    expected_ids: set[str],
    retrieved_ids: Sequence[str],
    k: int,
) -> float:
    if not expected_ids:
        raise ValueError("Expected document IDs cannot be empty.")

    if k < 1:
        raise ValueError("k must be greater than zero.")

    retrieved = retrieved_ids[:k]

    return len(expected_ids.intersection(retrieved)) / k


def reciprocal_rank(
    expected_ids: set[str],
    retrieved_ids: Sequence[str],
) -> float:
    if not expected_ids:
        raise ValueError("Expected document IDs cannot be empty.")

    for rank, document_id in enumerate(retrieved_ids, start=1):
        if document_id in expected_ids:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    relevance: Mapping[str, int],
    retrieved_ids: Sequence[str],
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k must be greater than zero.")

    score = 0.0

    for rank, document_id in enumerate(retrieved_ids[:k], start=1):
        grade = relevance.get(document_id, 0)

        if grade < 0:
            raise ValueError("Relevance grades cannot be negative.")

        gain = (2**grade) - 1
        discount = math.log2(rank + 1)

        score += gain / discount

    return score


def ndcg_at_k(
    relevance: Mapping[str, int],
    retrieved_ids: Sequence[str],
    k: int,
) -> float:
    if not relevance or not any(grade > 0 for grade in relevance.values()):
        raise ValueError("At least one relevant document is required.")

    actual_dcg = dcg_at_k(relevance, retrieved_ids, k)

    ideal_ids = sorted(
        relevance,
        key=lambda document_id: relevance[document_id],
        reverse=True,
    )

    ideal_dcg = dcg_at_k(relevance, ideal_ids, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg