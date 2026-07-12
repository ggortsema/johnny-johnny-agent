# Backlog Update: RAG Routing and Semantic Retrieval Foundations

**Date:** July 12, 2026  
**Story:** Johnny-Johnny RAG and Tool-Execution Learning Story  
**Status:** In Progress  
**Branch:** `dev`

## Completed Checkpoints

### Authenticated Assistant Routing

- Added an internal authenticated assistant invocation contract.
- Preserved `subject`, `scopes`, and `client_id` inside orchestration.
- Added a future `conversation_id` field without implementing chat memory yet.
- Kept identity and scopes out of OpenAI provider requests.
- Added model-based intent routing.
- Added initial routes:
  - `general_chat`
  - `backlog`
- Preserved normal general-chat behavior.
- Added a deterministic backlog placeholder before retrieval is connected.
- Verified both paths through the live authenticated REST endpoint.

### Retrieval Document Foundation

- Added a `backlog_retrieval` capability.
- Added deterministic epic retrieval documents.
- Added deterministic issue retrieval documents with parent-epic context.
- Excluded status, comments, provider metadata, labels, assignees, and order.
- Added SHA-256 source hashing.
- Proved that status-only changes do not change the document or hash.

### Embedding Foundation

- Selected `text-embedding-3-small`.
- Selected 1,536 dimensions.
- Added runtime embedding configuration.
- Added Kubernetes and `.env.example` configuration values.
- Added a provider-neutral embedding protocol.
- Added an OpenAI embedding adapter.
- Validated batching, ordering, dimensions, blank input, and malformed provider output.
- Made one real OpenAI embedding request and verified a 1,536-value vector.

### PostgreSQL Persistence Foundation

- Confirmed pgvector is installed in the `public` schema.
- Created `johnny_johnny.backlog_item_embeddings`.
- Established one current embedding row per canonical backlog item.
- Added SHA-256 and dimension constraints.
- Added `ON DELETE CASCADE`.
- Added an embedding repository with find and upsert behavior.
- Added refresh decision logic for created, updated, and unchanged states.
- Refresh skip requires matching source hash, model, and dimensions.

## Test State

Last complete-suite checkpoint before the later embedding persistence additions:

```text
151 passed
```

Focused tests completed afterward:

```text
test_backlog_retrieval_documents.py
test_openai_embedding_configuration.py
test_openai_embeddings.py
test_backlog_retrieval_postgres.py
test_backlog_embedding_refresh.py
```

All focused tests passed.

The complete suite has not yet been rerun after the final refresh-interface changes.

## Current Stopping Point

`RefreshBacklogItemEmbedding` and its focused tests are complete.

The real PostgreSQL embedding table exists but has not yet been populated with a canonical backlog item through the application refresh use case.

## Immediate Next Work

1. Run the full test suite.
2. Resolve any regressions before proceeding.
3. Wire a real canonical backlog item to `RefreshBacklogItemEmbedding`.
4. Generate and persist one real embedding row.
5. Read it back and inspect its metadata.
6. Add exact pgvector similarity search.
7. Embed the existing backlog in a controlled refresh command/use case.
8. Connect backlog-route classification to candidate retrieval.
9. Reload canonical candidate records.
10. Continue toward structured interpretation, confirmation, and existing mutation execution.

## Deferred but Required Later

- chat/conversation persistence for pronouns, follow-ups, and clarification;
- durable workflow checkpoint state before multi-request confirmation;
- authorization checks for specific proposed actions;
- semantic retrieval evaluation set;
- integration of embedding refresh with create/update/delete workflows;
- repair/reporting strategy for stale derived embeddings;
- LangChain retriever;
- LangGraph workflow and confirmation interrupt;
- execution through the existing mutation use case.
