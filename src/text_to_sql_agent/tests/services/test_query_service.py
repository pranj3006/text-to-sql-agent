from types import SimpleNamespace

import pytest

from text_to_sql_agent.app.services import query_service


class FakeMCPClient:
    async def call_tool(self, name, arguments):
        if name == "search_schema":
            return SimpleNamespace(
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
        if name == "validate_sql_tool":
            return SimpleNamespace(
                isError=False,
                structured_content={
                    "valid": True,
                    "normalized_sql": "SELECT customer_name FROM customers LIMIT 100",
                },
            )
        if name == "execute_readonly_sql":
            return SimpleNamespace(
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
        raise AssertionError(f"Unexpected tool: {name}")


@pytest.mark.asyncio
async def test_answer_query_orchestrates_service_adapters(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "generate_sql",
        lambda question, documents, *, engine: (
            "SELECT customer_name FROM customers"
        ),
    )

    result = await query_service.answer_query(
        "List customers",
        FakeMCPClient(),
        engine=SimpleNamespace(),
    )

    assert result["isError"] is False
    assert result["rows"] == [{"customer_name": "Alice"}]
