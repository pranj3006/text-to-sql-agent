import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def search_schema_tool(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:app@localhost/app_db")
    monkeypatch.setenv(
        "TEXT_TO_SQL_DATABASE_URL",
        "postgresql+asyncpg://app:app@localhost/analytics",
    )

    import text_to_sql_agent.mcp.tools.search_schema_tool as module

    importlib.reload(module)

    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    mcp = DummyMCP()
    module.register_search_schema_tools(mcp)

    return module, mcp.tools["search_schema"]


@pytest.fixture
def mock_retrieve_schema_documents(search_schema_tool, monkeypatch):
    module, search_schema = search_schema_tool
    mock = AsyncMock()
    monkeypatch.setattr(module, "retrieve_schema_documents", mock)
    return search_schema, mock


@pytest.mark.asyncio
async def test_search_schema_returns_matching_documents(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents

    mock_retrieve_schema_documents.return_value = [
        SimpleNamespace(
            document_id="table_orders",
            category="table",
            title="Orders",
            content="Contains customer order information.",
        ),
        SimpleNamespace(
            document_id="rule_recognized_revenue",
            category="business_rule",
            title="Recognized revenue",
            content="Only completed orders contribute to revenue.",
        ),
    ]

    response = await search_schema(
        query="revenue from orders",
        limit=5,
    )

    assert response.count == 2
    assert len(response.documents) == 2

    assert response.documents[0].document_id == "table_orders"
    assert response.documents[0].category == "table"
    assert response.documents[1].document_id == "rule_recognized_revenue"

    mock_retrieve_schema_documents.assert_awaited_once_with(
        query="revenue from orders",
        limit=5,
    )


@pytest.mark.asyncio
async def test_search_schema_strips_query_whitespace(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents
    mock_retrieve_schema_documents.return_value = []

    response = await search_schema(
        query="  revenue from orders  ",
        limit=3,
    )

    assert response.count == 0

    mock_retrieve_schema_documents.assert_awaited_once_with(
        query="revenue from orders",
        limit=3,
    )


@pytest.mark.asyncio
async def test_search_schema_returns_empty_results(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents
    mock_retrieve_schema_documents.return_value = []

    response = await search_schema(
        query="unknown business terminology",
    )

    assert response.count == 0
    assert response.documents == []


@pytest.mark.asyncio
async def test_search_schema_respects_limit(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents
    mock_retrieve_schema_documents.return_value = []

    await search_schema(
        query="customer orders",
        limit=3,
    )

    mock_retrieve_schema_documents.assert_awaited_once_with(
        query="customer orders",
        limit=3,
    )


@pytest.mark.asyncio
async def test_search_schema_rejects_whitespace_query(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents

    response = await search_schema(
        query="   ",
    )

    assert response.is_error is True
    assert response.content[0].text == "Error: 'query' cannot be an empty string."

    mock_retrieve_schema_documents.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_schema_propagates_retrieval_error(
    mock_retrieve_schema_documents,
):
    search_schema, mock_retrieve_schema_documents = mock_retrieve_schema_documents
    mock_retrieve_schema_documents.side_effect = RuntimeError(
        "Database connection failed"
    )

    with pytest.raises(RuntimeError, match="Database connection failed"):
        await search_schema(
            query="customer orders",
        )