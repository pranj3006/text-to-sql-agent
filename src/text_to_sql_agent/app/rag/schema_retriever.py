
from sqlalchemy import text
import re
from text_to_sql_agent.app.db.session import engine
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument

# English stop words that do not contribute meaningfully
# to schema document retrieval.
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "which",
    "with",
}

RETRIEVE_SCHEMA_SQL = text("""
    WITH query_terms AS (
        SELECT DISTINCT lexeme
        FROM unnest(
            tsvector_to_array(
                to_tsvector('english', :query)
            )
        ) AS lexeme
    ),
    search_query AS (
        SELECT
            to_tsquery(
                'english',
                string_agg(
                    quote_literal(lexeme),
                    ' | '
                )
            ) AS query
        FROM query_terms
    )
    SELECT
        document_id,
        category,
        title,
        content,
        ts_rank_cd(
            search_vector,
            search_query.query
        ) AS rank
    FROM schema_documents
    CROSS JOIN search_query
    WHERE search_vector @@ search_query.query
    ORDER BY rank DESC, document_id ASC
    LIMIT :limit
""")



def _build_or_tsquery(query: str) -> str:
    """
    Convert a natural-language query into a safe OR-based tsquery.

    Example:
        "total revenue by product category"

    Becomes:
        "total | revenue | product | category"

    PostgreSQL applies English stemming and stop-word handling.
    """

    if not query or not query.strip():
        return ""

    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())

    terms = []
    seen = set()

    for token in tokens:
        if token in STOP_WORDS or token in seen:
            continue

        seen.add(token)
        terms.append(token)

    return " | ".join(terms)


async def retrieve_schema_documents(
    query: str,
    limit: int = 5,
) -> list[SchemaDocument]:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if limit < 1:
        raise ValueError("limit must be greater than zero")

    tsquery = _build_or_tsquery(query)

    if not tsquery:
        return []

    async with engine.connect() as connection:
        result = await connection.execute(
            RETRIEVE_SCHEMA_SQL,
            {
                "query": query.strip(),
                "limit": limit,
            },
        )

        rows = result.mappings().all()

    return [
        SchemaDocument(
            document_id=row["document_id"],
            category=row["category"],
            title=row["title"],
            content=row["content"],
        )
        for row in rows
    ]

