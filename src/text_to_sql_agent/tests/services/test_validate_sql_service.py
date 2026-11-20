import pytest

from text_to_sql_agent.app.services.validate_sql_service import validate_sql


def test_validate_sql_accepts_select_and_applies_limit():
    sql = validate_sql(
        "SELECT customer_name FROM public.customers",
        dialect="postgres",
        allowed_tables=frozenset({"customers"}),
        schema="public",
    )

    assert "public.customers" in sql
    assert "LIMIT 100" in sql


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "DROP TABLE customers",
        "SELECT * FROM customers; SELECT * FROM orders",
        "SELECT * FROM secret_data",
        "SELECT pg_sleep(1)",
    ],
)
def test_validate_sql_rejects_unsafe_queries(sql):
    with pytest.raises(ValueError):
        validate_sql(
            sql,
            dialect="postgres",
            allowed_tables=frozenset({"customers"}),
            schema="public",
        )
