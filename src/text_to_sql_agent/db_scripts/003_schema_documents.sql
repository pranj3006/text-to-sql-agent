
-- Create schema_documents table for Schema RAG

CREATE TABLE IF NOT EXISTS schema_documents (
    document_id VARCHAR(150) PRIMARY KEY,

    category VARCHAR(50) NOT NULL,

    title TEXT NOT NULL,

    content TEXT NOT NULL,

    -- Automatically generated full-text search vector.
    -- Title receives higher relevance weight (A).
    -- Content receives lower relevance weight (B).
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


-- GIN index for PostgreSQL full-text search
CREATE INDEX IF NOT EXISTS idx_schema_documents_search
ON schema_documents
USING GIN (search_vector);


-- Index for filtering documents by category
CREATE INDEX IF NOT EXISTS idx_schema_documents_category
ON schema_documents (category);


-- Verify table creation
SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'schema_documents';
