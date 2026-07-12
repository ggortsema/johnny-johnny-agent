# Semantic Retrieval Database Design

**Date:** July 12, 2026  
**Database:** `styxcd`  
**Application schema:** `johnny_johnny`  
**Extension schema:** `public`  
**Migration:** `docs/database/postgres/003_create_backlog_item_embeddings.sql`

## Purpose

`backlog_item_embeddings` is a derived semantic-search index over canonical backlog items.

Canonical backlog state remains in `johnny_johnny.backlog_items`. The vector row helps locate a likely item from natural language but is never treated as the authoritative backlog record.

## Extension Placement

The pgvector extension is installed in `public`, which is a normal PostgreSQL arrangement.

Application tables remain in `johnny_johnny` and explicitly use:

```sql
public.vector(1536)
```

The extension should not be moved.

## Table

```sql
CREATE TABLE johnny_johnny.backlog_item_embeddings (
    backlog_item_id uuid PRIMARY KEY
        REFERENCES johnny_johnny.backlog_items(id)
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
```

## Relationship

```text
backlog_items
    1
    |
    | one current derived embedding
    |
    0..1
backlog_item_embeddings
```

`backlog_item_id` is both the primary key and foreign key. This guarantees one current embedding per canonical backlog item.

`ON DELETE CASCADE` removes the derived vector row when the canonical item is deleted.

## Stored Fields

### `source_text`

The exact deterministic text sent to the embedding provider.

Keeping the text makes the index inspectable and debuggable.

### `source_hash`

SHA-256 of `source_text`.

The refresh use case skips the provider call only when all of these match:

- source hash;
- embedding model;
- embedding dimensions.

### `embedding_model`

The model that created the vector, initially:

```text
text-embedding-3-small
```

### `embedding_dimensions`

The configured vector length, initially:

```text
1536
```

### `embedding`

The pgvector value used for semantic distance comparison.

### `embedded_at`

The time the current vector row was created or replaced.

## Source Document Recipe

### Epic

```text
Type
Title
Canonical ID
Description
Acceptance criteria
```

### Issue

```text
Type
Title
Canonical ID
Parent epic title
Parent epic canonical ID
Description
Acceptance criteria
```

Excluded initially:

```text
status
comments
labels
assignees
order
provider metadata
GitHub identifiers and URLs
```

Status and other operational fields are loaded from canonical tables after retrieval.

## Refresh Lifecycle

```text
No embedding row
→ generate vector
→ insert
→ status = created

Hash, model, and dimensions unchanged
→ skip provider call
→ status = unchanged

Text, model, or dimensions changed
→ generate vector
→ update current row
→ status = updated

Canonical item deleted
→ database cascade removes embedding row
```

The canonical mutation should not depend on a derived embedding write succeeding. A future integration must report or repair stale embeddings without misrepresenting canonical state.

## Search Strategy

The first version will use exact nearest-neighbor comparison. No HNSW or IVFFlat index is required for the current few-hundred-item corpus.

A future semantic search can combine exact structured filters with vector ranking:

```text
project
item type
epic
include statuses
exclude statuses
        +
semantic vector distance
```

Status does not need to be part of the embedding to be used as a filter.

## Migration and Rebuild Rules

Re-embed one item when its embedded descriptive source changes.

Rebuild all rows when:

- the embedding model changes;
- vector dimensions change;
- the source-document recipe changes globally.

A full rebuild is inexpensive at the current backlog size and does not alter canonical backlog data.
