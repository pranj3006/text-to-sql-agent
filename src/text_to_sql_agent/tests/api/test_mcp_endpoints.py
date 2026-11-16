from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

import text_to_sql_agent.app.main as main


class FakeMCPClient:
    def __init__(self) -> None:
        self.list_tools_calls = 0
        self.tool_calls: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self) -> "FakeMCPClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        pass

    async def list_tools(self) -> set[str]:
        self.list_tools_calls += 1
        return {"search_schema", "health_check"}

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> SimpleNamespace:
        self.tool_calls.append((tool_name, arguments))
        return SimpleNamespace(
            structured_content={
                "documents": [
                    {
                        "document_id": "table_orders",
                        "category": "table",
                        "title": "Orders",
                        "content": "Contains customer order information.",
                    }
                ],
                "count": 1,
            }
        )


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, FakeMCPClient]:
    mcp_client = FakeMCPClient()
    monkeypatch.setattr(main, "MCPClient", lambda _server_params: mcp_client)
    monkeypatch.setattr(main, "ensure_pgvector_extension", AsyncMock())
    monkeypatch.setattr(main, "dispose_query_database_engine", Mock())
    monkeypatch.setattr(type(main.engine), "dispose", AsyncMock())
    return TestClient(main.app), mcp_client


def test_mcp_endpoints_use_shared_client_and_return_structured_schema_results(
    api_client: tuple[TestClient, FakeMCPClient],
):
    test_client, mcp_client = api_client

    with test_client:
        tools_response = test_client.get("/mcp/tools")
        schema_response = test_client.get(
            "/mcp/schema-search",
            params={"query": "orders"},
        )

        assert main.app.state.mcp_client is mcp_client

    assert tools_response.status_code == 200
    assert tools_response.json() == {
        "tools": ["health_check", "search_schema"],
        "count": 2,
    }
    assert schema_response.status_code == 200
    assert schema_response.json() == {
        "documents": [
            {
                "document_id": "table_orders",
                "category": "table",
                "title": "Orders",
                "content": "Contains customer order information.",
            }
        ],
        "count": 1,
    }
    assert mcp_client.list_tools_calls == 1
    assert mcp_client.tool_calls == [
        ("search_schema", {"query": "orders", "limit": 5})
    ]
