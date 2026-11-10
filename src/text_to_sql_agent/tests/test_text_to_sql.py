import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

import text_to_sql_agent.app.text_to_sql as text_to_sql
from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.text_to_sql import (
    execute_sql,
    generate_sql,
    get_query_database_engine,
    get_schema_context,
    validate_sql,
)


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
                "INSERT INTO customers (customer_id, customer_name) "
                "VALUES (:customer_id, :customer_name)"
            ),
            [
                {
                    "customer_id": customer_id,
                    "customer_name": f"Customer {customer_id}",
                }
                for customer_id in range(105)
            ],
        )
    yield engine
    engine.dispose()


def test_schema_context_reflects_the_external_database(analytics_engine: Engine):
    schema_context = get_schema_context(analytics_engine)

    assert schema_context.dialect == "sqlite"
    assert schema_context.schema == "main"
    assert schema_context.tables == frozenset({"customers"})
    assert "customer_name TEXT" in schema_context.description


def test_generate_sql_uses_reflected_schema_and_dialect(
    analytics_engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    captured: dict[str, str] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {"output_text": "```sql\nSELECT customer_id FROM customers\n```"},
            )()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(text_to_sql, "_get_openai_client", lambda: FakeClient())

    sql = generate_sql("List customers", engine=analytics_engine)

    assert sql == "SELECT customer_id FROM customers"
    assert "SQL dialect: sqlite" in captured["input"]
    assert "customers(" in captured["input"]


def test_execute_sql_enforces_allowlist_and_row_cap(analytics_engine: Engine):
    result = execute_sql(
        "SELECT customer_id FROM customers ORDER BY customer_id",
        engine=analytics_engine,
    )

    assert result["row_count"] == 100
    assert result["rows"][0]["customer_id"] == 0
    assert '"main".' in result["sql"]
    assert "LIMIT 100" in result["sql"]

    with analytics_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO customers (customer_id, customer_name) "
                "VALUES (105, 'Query mode reset')"
            )
        )


def test_execute_sql_rejects_tables_outside_the_reflected_schema(
    analytics_engine: Engine,
):
    with pytest.raises(ValueError, match="unavailable table"):
        execute_sql("SELECT * FROM secret_data", engine=analytics_engine)


def test_validate_sql_supports_sql_server_dialect():
    sql = validate_sql(
        "SELECT customer_name FROM dbo.customers",
        dialect="tsql",
        allowed_tables=frozenset({"customers"}),
        schema="dbo",
        catalog="analytics",
    )

    assert "TOP" in sql.upper()


def test_validate_sql_does_not_casefold_allowlisted_identifiers():
    with pytest.raises(ValueError, match="unavailable table"):
        validate_sql(
            'SELECT * FROM "CUSTOMERS"',
            dialect="postgres",
            allowed_tables=frozenset({"customers"}),
            schema="public",
        )


def test_query_engine_does_not_fall_back_to_application_database(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TEXT_TO_SQL_DATABASE_URL", None)

    with pytest.raises(RuntimeError, match="TEXT_TO_SQL_DATABASE_URL"):
        get_query_database_engine()
