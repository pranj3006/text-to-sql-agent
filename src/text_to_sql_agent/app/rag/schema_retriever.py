
from sqlalchemy import text
from sqlalchemy.engine import Engine


RETRIEVE_SCHEMA = text("""
    SELECT
        document_id,
        category,
        title,
        content,
        ts_rank_cd(
            search_vector,
            websearch_to_tsquery('english', :query)
        ) AS relevance_score
    FROM schema_documents
    WHERE search_vector @@
        websearch_to_tsquery('english', :query)
    ORDER BY relevance_score DESC
    LIMIT :top_k
""")


def retrieve_schema_documents(
    engine: Engine,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not query or not query.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be greater than zero")

    with engine.connect() as connection:
        result = connection.execute(
            RETRIEVE_SCHEMA,
            {
                "query": query.strip(),
                "top_k": top_k,
            },
        )

        return [
            dict(row)
            for row in result.mappings()
        ]
