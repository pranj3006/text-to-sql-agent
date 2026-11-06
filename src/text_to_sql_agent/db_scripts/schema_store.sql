
CREATE TABLE IF NOT EXISTS schema_documents (
    document_id VARCHAR(150) PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,

    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(
            to_tsvector('english', COALESCE(title, '')),
            'A'
        )
        ||
        setweight(
            to_tsvector('english', COALESCE(content, '')),
            'B'
        )
    ) STORED,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schema_documents_search
ON schema_documents
USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_schema_documents_category
ON schema_documents (category);
