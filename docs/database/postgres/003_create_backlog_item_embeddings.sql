-- Derived semantic retrieval index for canonical backlog items
-- Story: Johnny-Johnny RAG and Tool-Execution Learning Story
-- Embedding model: text-embedding-3-small
-- Vector dimensions: 1536

BEGIN;

SET search_path TO johnny_johnny;

CREATE TABLE IF NOT EXISTS backlog_item_embeddings (
                                                       backlog_item_id uuid PRIMARY KEY
                                                       REFERENCES backlog_items(id)
    ON DELETE CASCADE,

    source_text text NOT NULL,
    source_hash text NOT NULL,

    embedding_model text NOT NULL,
    embedding_dimensions integer NOT NULL,

    embedding public.vector(1536) NOT NULL,

    embedded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_backlog_item_embeddings_source_hash
    CHECK (source_hash ~ '^[0-9a-f]{64}$'),

    CONSTRAINT ck_backlog_item_embeddings_dimensions
    CHECK (embedding_dimensions = 1536)
    );

COMMIT;