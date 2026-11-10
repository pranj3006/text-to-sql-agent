from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from text_to_sql_agent.app.db.models import SchemaDocumentModel


def test_schema_document_model_matches_postgres_table_definition():
    table = SchemaDocumentModel.__table__

    assert table.schema == "public"
    assert table.primary_key.columns.keys() == ["document_id"]
    assert table.c.document_id.type.length == 150
    assert table.c.category.type.length == 50
    assert table.c.title.nullable is False
    assert table.c.content.nullable is False
    assert table.c.search_vector.computed.persisted is True
    assert "to_tsvector('english'::regconfig" in str(
        table.c.search_vector.computed.sqltext
    )
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None
    assert table.c.updated_at.onupdate is not None


def test_schema_document_model_defines_category_and_single_gin_indexes():
    indexes = {index.name: index for index in SchemaDocumentModel.__table__.indexes}

    assert set(indexes) == {
        "idx_schema_documents_category",
        "idx_schema_documents_search",
    }
    assert indexes["idx_schema_documents_search"].dialect_options[
        "postgresql"
    ]["using"] == "gin"


def test_schema_document_ddl_compiles_for_postgresql():
    ddl = str(
        CreateTable(SchemaDocumentModel.__table__).compile(
            dialect=postgresql.dialect()
        )
    )

    assert "GENERATED ALWAYS AS" in ddl
    assert "TSVECTOR" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
