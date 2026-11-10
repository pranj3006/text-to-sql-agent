from sqlalchemy import Computed, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from text_to_sql_agent.app.db.base import Base, TimestampMixin


class SchemaDocumentModel(TimestampMixin, Base):
    __tablename__ = "schema_documents"
    __table_args__ = (
        Index("idx_schema_documents_category", "category"),
        Index(
            "idx_schema_documents_search",
            "search_vector",
            postgresql_using="gin",
        ),
        {"schema": "public"},
    )

    document_id: Mapped[str] = mapped_column(String(150), primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            """setweight(to_tsvector('english'::regconfig, COALESCE(title, ''::text)), 'A'::"char")
            || setweight(to_tsvector('english'::regconfig, COALESCE(content, ''::text)), 'B'::"char")""",
            persisted=True,
        ),
    )
