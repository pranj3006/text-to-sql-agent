
from text_to_sql_agent.app.rag.schema_documents import get_schema_documents


def test_schema_documents_have_unique_ids():
    documents = get_schema_documents()
    ids = [document.document_id for document in documents]

    assert len(ids) == len(set(ids))


def test_required_tables_are_documented():
    documents = get_schema_documents()
    content = "\n".join(document.content for document in documents)

    for table in (
        "customers",
        "products",
        "orders",
        "order_items",
    ):
        assert table in content


def test_revenue_business_rules_are_documented():
    documents = get_schema_documents()
    content = "\n".join(document.content for document in documents)

    assert "discount_pct" in content
    assert "completed" in content
    assert "cancelled" in content


def test_documents_have_required_fields():
    for document in get_schema_documents():
        assert document.document_id
        assert document.category
        assert document.title
        assert document.content.strip()
