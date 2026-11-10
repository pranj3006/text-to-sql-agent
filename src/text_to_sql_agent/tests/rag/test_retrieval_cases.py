
from text_to_sql_agent.app.rag.schema_documents import get_schema_documents
import pytest
from text_to_sql_agent.evaluation.rag.retrieval_cases import RETRIEVAL_TEST_CASES


def test_retrieval_cases_reference_existing_documents():
    document_ids = {
        document.document_id
        for document in get_schema_documents()
    }

    for case in RETRIEVAL_TEST_CASES:
        unknown_ids = set(case.relevance) - document_ids

        assert not unknown_ids, (
            f"{case.case_id} references unknown documents: {unknown_ids}"
        )


def test_retrieval_cases_have_valid_relevance_grades():
    for case in RETRIEVAL_TEST_CASES:
        assert case.relevance

        for grade in case.relevance.values():
            assert grade in (1, 2)


def test_retrieval_case_ids_are_unique():
    case_ids = [
        case.case_id
        for case in RETRIEVAL_TEST_CASES
    ]

    assert len(case_ids) == len(set(case_ids))


def test_benchmark_contains_fifteen_cases():
    assert len(RETRIEVAL_TEST_CASES) == 15
