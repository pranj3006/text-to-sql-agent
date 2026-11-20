from types import SimpleNamespace

from text_to_sql_agent.app.rag.schema_documents import SchemaDocument
from text_to_sql_agent.app.services import generate_sql_service


def test_generate_sql_strips_code_fence(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text="```sql\nSELECT customer_name FROM customers\n```"
            )

    monkeypatch.setattr(
        generate_sql_service.core,
        "get_schema_context",
        lambda engine: SimpleNamespace(
            description="SQL dialect: sqlite\ncustomers(customer_name TEXT)",
        ),
    )
    monkeypatch.setattr(
        generate_sql_service.core,
        "_get_openai_client",
        lambda: SimpleNamespace(responses=FakeResponses()),
    )

    document = SchemaDocument(
        document_id="table_customers",
        category="table",
        title="Customers",
        content="Table: customers",
    )

    sql = generate_sql_service.generate_sql(
        "List customer names",
        [document],
        engine=SimpleNamespace(),
    )

    assert sql == "SELECT customer_name FROM customers"
    assert "Table: customers" in captured["input"]
    assert "List customer names" in captured["input"]
