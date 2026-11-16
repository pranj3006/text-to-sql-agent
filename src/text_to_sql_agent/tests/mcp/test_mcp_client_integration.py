import os
import sys
from pathlib import Path

import pytest
from mcp import StdioServerParameters

from text_to_sql_agent.mcp.mcp_client_module import MCPClient


PROJECT_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_client_communicates_with_standalone_server_over_stdio():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "text_to_sql_agent.mcp.mcp_server"],
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/app_db",
            "TEXT_TO_SQL_DATABASE_URL": (
                "postgresql+psycopg://test:test@localhost/business_db"
            ),
            "OPENAI_API_KEY": "",
        },
    )

    async with MCPClient(server_params) as client:
        tools = await client.list_tools()

        assert tools == {
            "health_check",
            "search_schema",
            "validate_sql_tool",
            "execute_readonly_sql",
        }

        health_result = await client.call_tool("health_check", {})
        assert health_result.is_error is False
        assert health_result.structured_content == {
            "status": "ok",
            "service": "text-to-sql-mcp",
        }

        validation_result = await client.call_tool(
            "validate_sql_tool",
            {"sql": "SELECT * FROM customers"},
        )
        assert validation_result.is_error is False
        assert validation_result.structured_content == {
            "valid": True,
            "normalized_sql": 'SELECT * FROM "public".customers LIMIT 100',
            "error": None,
        }
