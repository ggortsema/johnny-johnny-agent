# Session Index

**Date:** July 12, 2026  
**Project:** Johnny-Johnny Agent  
**Project Version:** 0.1.0  
**Git Branch:** `dev`  
**Current Story:** Johnny-Johnny RAG and Tool-Execution Learning Story  
**Current Phase:** Authenticated routing and semantic retrieval foundation  
**Next Story:** Continue the current RAG story; do not begin a new story yet

## Session Summary

This session began with a conceptual walkthrough of how Johnny-Johnny will convert a natural-language backlog request into a safe canonical mutation.

The design was refined to account for Johnny-Johnny's broad future scope. A model-based router now classifies each authenticated message before any domain retrieval. General chat continues through the existing assistant path. Backlog requests enter a dedicated path and currently stop at a deterministic placeholder.

The session then built the semantic retrieval foundation:

```text
canonical backlog item
→ deterministic retrieval document
→ SHA-256 source hash
→ OpenAI embedding
→ PostgreSQL pgvector row
→ refresh decision
```

The pgvector table was created successfully. A real OpenAI embedding call returned a validated 1,536-value vector. Repository and refresh behavior were proven with focused tests.

The session ended before the first real canonical backlog item was persisted through the refresh use case.

## Story Progress

### Current Story: Johnny-Johnny RAG and Tool-Execution Learning Story

Completed in this session:

- authenticated principal propagation;
- provider-boundary identity sanitization;
- model-based assistant route classification;
- live general-chat and backlog-route verification;
- deterministic backlog retrieval documents;
- source hashing;
- embedding configuration;
- provider-neutral embedding interface;
- OpenAI embedding adapter;
- real embedding generation;
- pgvector table migration;
- embedding repository;
- embedding refresh decision use case.

Not yet completed:

- full-suite verification after the final refresh changes;
- real embedding persistence through the application use case;
- similarity search;
- bulk backlog ingestion;
- canonical candidate reload;
- structured mutation interpretation;
- confirmation persistence;
- LangChain integration;
- LangGraph orchestration;
- confirmed mutation execution.

## Engineering Artifacts Created

- `ADR-assistant-routing-and-semantic-retrieval-2026-07-12.md`
- `semantic-retrieval-database-design-2026-07-12.md`
- `BACKLOG-UPDATE-2026-07-12-rag-foundations.md`
- `command-cheat-sheet-2026-07-12-182916.md`
- `session-index.md`

## Engineering Artifacts Updated in the Repository

Expected changed or added files based on the session work:

```text
.env
.env.example
docs/database/postgres/003_create_backlog_item_embeddings.sql
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml

src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/capabilities/assistant/models.py
src/johnny_johnny_agent/capabilities/assistant/use_case.py
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/providers/openai_language_model.py

src/johnny_johnny_agent/capabilities/backlog_retrieval/__init__.py
src/johnny_johnny_agent/capabilities/backlog_retrieval/documents.py
src/johnny_johnny_agent/capabilities/backlog_retrieval/postgres.py
src/johnny_johnny_agent/capabilities/backlog_retrieval/refresh.py

src/johnny_johnny_agent/capabilities/semantic_retrieval/__init__.py
src/johnny_johnny_agent/capabilities/semantic_retrieval/embeddings.py
src/johnny_johnny_agent/providers/openai_embeddings.py

tests/behavior/test_backlog_rest_api.py
tests/unit/test_assistant_response.py
tests/unit/test_openai_language_model.py
tests/unit/test_backlog_retrieval_documents.py
tests/unit/test_openai_embedding_configuration.py
tests/unit/test_openai_embeddings.py
tests/unit/test_backlog_retrieval_postgres.py
tests/unit/test_backlog_embedding_refresh.py
```

The next session should verify this list against the new project archive and `git status`.

## Architectural Decisions

- Route before retrieval for Johnny-Johnny.
- Use a model classifier, not Python keyword matching.
- Retain authenticated subject and scopes inside orchestration.
- Do not send identity or scopes to OpenAI.
- Invoke internal application use cases directly rather than calling Johnny-Johnny's REST API from itself.
- Reserve `conversation_id` now; defer full chat memory.
- Use domain-specific retrieval tables with a shared embedding interface.
- Store one current embedding per backlog item.
- Embed both epics and issues.
- Include parent epic title and canonical ID in issue documents.
- Exclude status and comments initially.
- Reload operational state from canonical tables after retrieval.
- Use `text-embedding-3-small` at 1,536 dimensions.
- Keep pgvector extension objects in `public`.
- Keep application tables in `johnny_johnny`.
- Use exact vector search initially; defer HNSW/IVFFlat.
- Refresh only when source hash, model, or dimensions differ.

## Database Decisions

- Created `johnny_johnny.backlog_item_embeddings`.
- `backlog_item_id` is the primary key and foreign key.
- `ON DELETE CASCADE` removes derived embedding rows.
- `source_hash` must be a lowercase 64-character SHA-256 hex value.
- `embedding_dimensions` is constrained to 1,536.
- `embedding` uses `public.vector(1536)`.
- No approximate vector index was added.

## Bugs Discovered and Resolved

### Wrong `models.py` edited

The assistant contracts were initially pasted into `api/models.py` instead of `capabilities/assistant/models.py`.

The on-disk path check exposed the mismatch.

### Assistant provider method misplaced

A method replacement left `generate()` outside `OpenAILanguageModelProvider`.

A whole-file replacement restored the class structure.

### Duplicate pasted provider content

`openai_embeddings.py` temporarily contained duplicate content, placing a `from __future__` import below existing code.

The file was fully replaced.

### Circular self-import

Provider-specific imports were accidentally placed in the provider-neutral `semantic_retrieval/embeddings.py`, causing a circular import.

The interface file was restored to provider-neutral contracts only.

### Kubernetes YAML editor folding confusion

IntelliJ visually folded `name` and `value` mappings, making correct YAML appear similar to invalid shorthand. The actual manifest uses standard Kubernetes environment mappings.

## Lessons Learned

- Verify the exact file path when multiple modules have the same filename.
- Prefer complete file replacement when structural indentation is uncertain.
- Run focused import or unit tests after every interface change.
- Keep authentication context separate from model-provider payloads.
- Vector search always returns nearest rows; route unrelated messages before retrieval.
- Embeddings represent searchable meaning, not canonical truth.
- Stable descriptive fields reduce re-embedding churn.
- Exact structured filters can be combined with vector ranking later.
- The vector index is inexpensive and rebuildable at the current corpus size.

## Test Checkpoint

Verified:

```text
151 passed
```

This full-suite checkpoint occurred before the final embedding repository and refresh work.

All subsequent focused tests passed.

Not yet verified:

```text
uv run pytest
```

after the final refresh-interface changes.

## Outstanding Work

- run the full test suite;
- inspect `git status`;
- persist one real canonical backlog item embedding;
- verify the row through PostgreSQL;
- add exact similarity search;
- create controlled bulk refresh/ingestion;
- evaluate known natural-language prompts;
- connect backlog routing to retrieval;
- reload canonical candidate records;
- add structured action interpretation;
- add conversation and workflow persistence;
- add explicit confirmation;
- authorize proposed actions using principal scopes;
- exercise the existing mutation use case;
- normalize partial provider-sync failures;
- add LangChain;
- add LangGraph.

## Next Recommended Starting Point

Use the newly uploaded current project archive as the source of truth.

First run:

```bash
uv run pytest
```

Do not proceed until the complete suite passes.

Then wire one known canonical issue and its parent epic into `RefreshBacklogItemEmbedding`, persist one real row, and read it back.

## Files Likely Needed Next Session

```text
current johnny-johnny-agent archive from branch dev
docs/development/WORKING_AGREEMENT.md
docs/development/ENGINEERING_PRINCIPLES.md
johnny-johnny-rag-tool-execution-story.md
ADR-assistant-routing-and-semantic-retrieval-2026-07-12.md
semantic-retrieval-database-design-2026-07-12.md
BACKLOG-UPDATE-2026-07-12-rag-foundations.md
docs/database/postgres/003_create_backlog_item_embeddings.sql
```

## Immediate First Task

1. Extract and inspect the new archive.
2. Run the full suite.
3. Compare actual changed files with this index.
4. Persist one real backlog-item embedding through the refresh use case.
