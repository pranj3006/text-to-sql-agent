"""create schema documents

Revision ID: ef3a65e3fc1f
Revises: 
Create Date: 2026-11-10 05:17:15.891937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ef3a65e3fc1f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "schema_documents",
        sa.Column("document_id", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                """setweight(to_tsvector('english'::regconfig, COALESCE(title, ''::text)), 'A'::"char")
                || setweight(to_tsvector('english'::regconfig, COALESCE(content, ''::text)), 'B'::"char")""",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("document_id", name="schema_documents_pkey"),
        schema="public",
    )
    op.create_index(
        "idx_schema_documents_category",
        "schema_documents",
        ["category"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "idx_schema_documents_search",
        "schema_documents",
        ["search_vector"],
        unique=False,
        schema="public",
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("schema_documents", schema="public")
