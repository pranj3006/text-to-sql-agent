import pytest

from text_to_sql_agent.app.rag.schema_retriever import (
    _build_or_tsquery,
    retrieve_schema_documents,
)


def test_build_or_tsquery():
    result = _build_or_tsquery(
        "What is the total revenue by product category?"
    )

    assert result == "total | revenue | product | category"


def test_build_or_tsquery_removes_duplicates():
    result = _build_or_tsquery("revenue revenue sales")

    assert result == "revenue | sales"


def test_build_or_tsquery_empty_input():
    assert _build_or_tsquery("") == ""


@pytest.mark.asyncio
async def test_retrieve_schema_documents():
    documents = await retrieve_schema_documents(
        query="revenue OR product OR category",
        limit=5,
    )

    assert isinstance(documents, list)
    assert len(documents) > 0
    assert len(documents) <= 5

    for document in documents:
        assert document.document_id
        assert document.category
        assert document.title
        assert document.content


@pytest.mark.asyncio
async def test_retrieve_schema_documents_empty_query():
    with pytest.raises(ValueError):
        await retrieve_schema_documents("")


@pytest.mark.asyncio
async def test_retrieve_schema_documents_invalid_limit():
    with pytest.raises(ValueError):
        await retrieve_schema_documents(
            query="revenue",
            limit=0,
        )