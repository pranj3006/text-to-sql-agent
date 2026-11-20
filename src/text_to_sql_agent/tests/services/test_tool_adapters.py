from types import SimpleNamespace

import pytest

from text_to_sql_agent.app.services.search_schema_service import search_schema_tool_call
from text_to_sql_agent.app.services.validate_sql_service import validate_sql_tool_call
from text_to_sql_agent.app.services.execute_sql_service import execute_sql_tool_call


class FakeMCPClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results[name]


@pytest.mark.asyncio
async def test_search_schema_adapter_converts_documents():
    client = FakeMCPClient({
        "search_schema": SimpleNamespace(
            isError=False,
            structured_content={
                "documents": [{
                    "document_id": "table_customers",
                    "category": "table",
                    "title": "Customers",
                    "content": "Table: customers",
                }]
            },
        )
    })

    result = await search_schema_tool_call("List customers", client)

    assert result["isError"] is False
    assert result["relevant_documents"][0].document_id == "table_customers"


@pytest.mark.asyncio
async def test_validate_adapter_returns_normalized_sql():
    client = FakeMCPClient({
        "validate_sql_tool": SimpleNamespace(
            isError=False,
            structured_content={
                "valid": True,
                "normalized_sql": "SELECT customer_name FROM customers LIMIT 100",
            },
        )
    })

    result = await validate_sql_tool_call("SELECT customer_name FROM customers", client)

    assert result["validated_sql"].endswith("LIMIT 100")


@pytest.mark.asyncio
async def test_execute_adapter_returns_result():
    client = FakeMCPClient({
        "execute_readonly_sql": SimpleNamespace(
            isError=False,
            structured_content={
                "success": True,
                "sql": "SELECT customer_name FROM customers LIMIT 100",
                "columns": ["customer_name"],
                "rows": [{"customer_name": "Alice"}],
                "row_count": 1,
                "error": None,
            },
        )
    })

    result = await execute_sql_tool_call(
        "SELECT customer_name FROM customers",
        client,
        question="List customers",
    )

    assert result["isError"] is False
    assert result["rows"] == [{"customer_name": "Alice"}]
