import pytest

from text_to_sql_agent.evaluation.rag.metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k():
    expected = {"doc1", "doc2", "doc3"}
    retrieved = ["doc1", "doc4", "doc2"]

    assert recall_at_k(expected, retrieved, 3) == pytest.approx(2 / 3)


def test_precision_at_k():
    expected = {"doc1", "doc2", "doc3"}
    retrieved = ["doc1", "doc4", "doc2", "doc5", "doc3"]

    assert precision_at_k(expected, retrieved, 5) == pytest.approx(3 / 5)


def test_precision_at_k_when_fewer_documents_returned():
    expected = {"doc1", "doc2"}
    retrieved = ["doc1"]

    assert precision_at_k(expected, retrieved, 5) == pytest.approx(1 / 5)


def test_reciprocal_rank():
    expected = {"doc1", "doc2"}
    retrieved = ["doc4", "doc5", "doc2", "doc1"]

    assert reciprocal_rank(expected, retrieved) == pytest.approx(1 / 3)


def test_reciprocal_rank_when_no_relevant_document():
    expected = {"doc1", "doc2"}
    retrieved = ["doc3", "doc4"]

    assert reciprocal_rank(expected, retrieved) == 0.0


def test_empty_expected_documents():
    with pytest.raises(ValueError):
        recall_at_k(set(), ["doc1"], 3)


def test_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k({"doc1"}, ["doc1"], 0)