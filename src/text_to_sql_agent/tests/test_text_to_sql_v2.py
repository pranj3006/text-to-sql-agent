from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

import text_to_sql_agent.app.text_to_sql_v2 as text_to_sql_v2
from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument


@pytest.fixture
def analytics_engine(monkeypatch: pytest.MonkeyPatch) -> Engine:
    monkeypatch.setattr(settings, "TEXT_TO_SQL_SCHEMA", None)
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE customers "
                "(customer_id INTEGER PRIMARY KEY, customer_name TEXT)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE orders "
                "(order_id INTEGER PRIMARY KEY, customer_id INTEGER "
                "REFERENCES customers(customer_id), amount NUMERIC)"
            )
        )
        connection.execute(
            text("INSERT INTO customers VALUES (1, 'Alice')")
        )
        connection.execute(
            text("INSERT INTO orders VALUES (1, 1, 12.5)")
        )
        connection.execute(
            text(
                "CREATE VIEW customer_names AS "
                "SELECT customer_id, customer_name FROM customers"
            )
        )
    yield engine
    engine.dispose()


def make_tool_result(*, structured_content=None, is_error=False, text_value=None):
    return SimpleNamespace(
        structured_content=structured_content,
        isError=is_error,
        content=[SimpleNamespace(text=text_value)] if text_value else [],
    )


def test_schema_context_includes_tables_views_and_relationships(
    analytics_engine: Engine,
):
    context = text_to_sql_v2.get_schema_context(analytics_engine)

    assert context.dialect == "sqlite"
    assert context.schema == "main"
    assert context.tables == frozenset(
        {"customers", "customer_names", "orders"}
    )
    assert "customer_name TEXT" in context.description
    assert "Relationship: orders.customer_id -> main.customers.customer_id" in (
        context.description
    )


def test_prepare_relevant_documents_instructions_formats_documents():
    document = SchemaDocument(
        document_id="table_orders",
        category="table",
        title="Orders",
        content="Contains customer order information.",
    )

    assert text_to_sql_v2.prepare_relevant_documents_instructions([]) == "None"
    assert text_to_sql_v2.prepare_relevant_documents_instructions([document]) == (
        "Document: Orders\n"
        "Category: table\n"
        "Content:\nContains customer order information.\n"
    )


def test_generate_sql_uses_schema_context_and_removes_code_fences(
    analytics_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    document = SchemaDocument(
        document_id="table_orders",
        category="table",
        title="Orders",
        content="Contains customer order information.",
    )

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text="```sql\nSELECT order_id FROM orders\n```"
            )

    monkeypatch.setattr(
        text_to_sql_v2,
        "_get_openai_client",
        lambda: SimpleNamespace(responses=FakeResponses()),
    )

    sql = text_to_sql_v2.generate_sql(
        "List orders",
        [document],
        engine=analytics_engine,
    )

    assert sql == "SELECT order_id FROM orders"
    assert captured["model"] == settings.OPENAI_MODEL
    assert "SQL dialect: sqlite" in captured["input"]
    assert "Document: Orders" in captured["input"]
    assert "USER QUESTION:\n            List orders" in captured["input"]


@pytest.mark.parametrize(
    ("sql", "expected_fragment"),
    [
        ("SELECT order_id FROM orders LIMIT 5", "LIMIT 5"),
        ("SELECT order_id FROM orders LIMIT 500", "LIMIT 100"),
        ("SELECT order_id FROM orders", "LIMIT 100"),
    ],
)
def test_validate_sql_allows_query_and_caps_row_limit(
    sql: str,
    expected_fragment: str,
):
    normalized_sql = text_to_sql_v2.validate_sql(
        sql,
        allowed_tables=frozenset({"orders"}),
        schema="public",
    )

    assert expected_fragment in normalized_sql
    assert '"public".orders' in normalized_sql


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("DELETE FROM orders", "Only read-only SELECT"),
        ("SELECT * FROM orders; SELECT 1", "Exactly one SQL statement"),
        ("SELECT pg_sleep(1)", "prohibited function"),
        ("SELECT * FROM private.orders", "unavailable schema"),
        ("SELECT * FROM customers", "unavailable table or view"),
    ],
)
def test_validate_sql_rejects_unsafe_or_unavailable_queries(
    sql: str,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        text_to_sql_v2.validate_sql(
            sql,
            allowed_tables=frozenset({"orders"}),
            schema="public",
        )


def test_validate_sql_rejects_invalid_sql():
    with pytest.raises(ValueError, match="could not be parsed"):
        text_to_sql_v2.validate_sql("SELECT FROM")


def test_execute_sql_returns_rows_and_json_safe_values(
    analytics_engine: Engine,
):
    result = text_to_sql_v2.execute_sql(
        "SELECT amount FROM orders",
        engine=analytics_engine,
    )

    assert result["row_count"] == 1
    assert result["columns"] == ["amount"]
    assert result["rows"] == [{"amount": 12.5}]
    assert result["sql"].startswith("SELECT")

    with analytics_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO customers VALUES (2, 'Bob')")
        )


def test_execute_sql_rejects_unavailable_table(analytics_engine: Engine):
    with pytest.raises(ValueError, match="unavailable table or view"):
        text_to_sql_v2.execute_sql(
            "SELECT * FROM private_data",
            engine=analytics_engine,
        )


@pytest.mark.asyncio
async def test_answer_question_converts_documents_and_returns_execution_result(
    monkeypatch: pytest.MonkeyPatch,
):
    schema_document = {
        "document_id": "table_orders",
        "category": "table",
        "title": "Orders",
        "content": "Contains customer order information.",
    }
    relevant_documents: list[SchemaDocument] = []

    def fake_generate_sql(question, documents, *, engine):
        relevant_documents.extend(documents)
        return "SELECT 1"

    monkeypatch.setattr(text_to_sql_v2, "generate_sql", fake_generate_sql)
    client = SimpleNamespace(
        call_tool=AsyncMock(
            side_effect=[
                make_tool_result(
                    structured_content={
                        "documents": [schema_document],
                        "count": 1,
                    }
                ),
                make_tool_result(
                    structured_content={
                        "valid": True,
                        "normalized_sql": "SELECT 1 LIMIT 100",
                    }
                ),
                make_tool_result(
                    structured_content={
                        "success": True,
                        "sql": "SELECT 1 LIMIT 100",
                        "columns": ["?column?"],
                        "rows": [{"?column?": 1}],
                        "row_count": 1,
                    }
                ),
            ]
        )
    )

    response = await text_to_sql_v2.answer_question(
        "List orders",
        client,
        engine=object(),
    )

    assert relevant_documents == [
        SchemaDocument(
            document_id="table_orders",
            category="table",
            title="Orders",
            content="Contains customer order information.",
        )
    ]
    assert all(isinstance(doc, SchemaDocument) for doc in relevant_documents)
    assert response == {
        "question": "List orders",
        "success": True,
        "sql": "SELECT 1 LIMIT 100",
        "columns": ["?column?"],
        "rows": [{"?column?": 1}],
        "row_count": 1,
        "model": settings.OPENAI_MODEL,
        "approach": "baseline_dynamic_schema",
    }
    assert client.call_tool.await_args_list == [
        call("search_schema", {"query": "List orders", "limit": 5}),
        call("validate_sql_tool", {"sql": "SELECT 1"}),
        call("execute_readonly_sql", {"sql": "SELECT 1 LIMIT 100"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("validation_result", "expected_error"),
    [
        (
            make_tool_result(
                structured_content={"valid": False, "error": "Unsafe SQL"}
            ),
            "Unsafe SQL",
        ),
        (
            make_tool_result(is_error=True, text_value="Validator unavailable"),
            "Validator unavailable",
        ),
    ],
)
async def test_answer_question_returns_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    validation_result,
    expected_error: str,
):
    monkeypatch.setattr(
        text_to_sql_v2,
        "generate_sql",
        lambda question, documents, *, engine: "SELECT 1",
    )
    client = SimpleNamespace(
        call_tool=AsyncMock(
            side_effect=[
                make_tool_result(structured_content={"documents": [], "count": 0}),
                validation_result,
            ]
        )
    )

    response = await text_to_sql_v2.answer_question("List orders", client, engine=object())

    assert response["error"] == expected_error
    assert [entry.args[0] for entry in client.call_tool.await_args_list] == [
        "search_schema",
        "validate_sql_tool",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("execution_result", "expected_error"),
    [
        (
            make_tool_result(
                structured_content={
                    "success": False,
                    "error": "Execution rejected",
                    "rows": [],
                    "columns": [],
                    "row_count": 0,
                }
            ),
            "Execution rejected",
        ),
        (
            make_tool_result(is_error=True, text_value="Executor unavailable"),
            "Executor unavailable",
        ),
    ],
)
async def test_answer_question_returns_execution_errors(
    monkeypatch: pytest.MonkeyPatch,
    execution_result,
    expected_error: str,
):
    monkeypatch.setattr(
        text_to_sql_v2,
        "generate_sql",
        lambda question, documents, *, engine: "SELECT 1",
    )
    client = SimpleNamespace(
        call_tool=AsyncMock(
            side_effect=[
                make_tool_result(structured_content={"documents": [], "count": 0}),
                make_tool_result(
                    structured_content={
                        "valid": True,
                        "normalized_sql": "SELECT 1 LIMIT 100",
                    }
                ),
                execution_result,
            ]
        )
    )

    response = await text_to_sql_v2.answer_question("List orders", client, engine=object())

    assert response["error"] == expected_error
    assert len(client.call_tool.await_args_list) == 3
