import importlib
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sql_validation_tool(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/app_db")
    monkeypatch.setenv("TEXT_TO_SQL_DATABASE_URL", "postgresql://localhost/analytics")

    import text_to_sql_agent.mcp.tools.sql_validation_tool as module

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
    module.register_sql_tools(mcp)

    return module, mcp.tools["validate_sql_tool"]


def test_validate_sql_tool_accepts_valid_sql(sql_validation_tool, monkeypatch):
    module, validate_sql_tool = sql_validation_tool
    mock_validate_sql = MagicMock(return_value="SELECT * FROM customers LIMIT 100")
    monkeypatch.setattr(module, "validate_sql", mock_validate_sql)

    response = validate_sql_tool("  SELECT * FROM customers  ")

    assert response.valid is True
    assert response.normalized_sql == "SELECT * FROM customers LIMIT 100"
    assert response.error is None
    mock_validate_sql.assert_called_once_with(
        "SELECT * FROM customers",
        dialect="postgres",
        allowed_tables=module.ALLOWED_TABLES,
        schema=module.TARGET_SCHEMA,
        catalog=module.TARGET_CATALOG,
    )


def test_validate_sql_tool_rejects_blank_sql(sql_validation_tool, monkeypatch):
    module, validate_sql_tool = sql_validation_tool
    mock_validate_sql = MagicMock()
    monkeypatch.setattr(module, "validate_sql", mock_validate_sql)

    response = validate_sql_tool("   \n\t  ")

    assert response.valid is False
    assert response.normalized_sql is None
    assert response.error == "SQL query cannot be empty or whitespace only."
    mock_validate_sql.assert_not_called()


def test_validate_sql_tool_returns_validation_error(sql_validation_tool, monkeypatch):
    module, validate_sql_tool = sql_validation_tool
    mock_validate_sql = MagicMock(side_effect=ValueError("Unsafe query"))
    monkeypatch.setattr(module, "validate_sql", mock_validate_sql)

    response = validate_sql_tool("SELECT pg_sleep(1)")

    assert response.valid is False
    assert response.normalized_sql is None
    assert response.error == "Unsafe query"
    mock_validate_sql.assert_called_once_with(
        "SELECT pg_sleep(1)",
        dialect="postgres",
        allowed_tables=module.ALLOWED_TABLES,
        schema=module.TARGET_SCHEMA,
        catalog=module.TARGET_CATALOG,
    )
