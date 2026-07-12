# ADR: Authenticated Assistant Routing and Domain-Specific Semantic Retrieval

**Date:** July 12, 2026  
**Status:** Accepted  
**Project:** Johnny-Johnny Agent  
**Story:** Johnny-Johnny RAG and Tool-Execution Learning Story

## Context

Johnny-Johnny already had:

- an OAuth-protected assistant endpoint;
- a provider-neutral assistant use case;
- canonical backlog state in PostgreSQL;
- targeted backlog mutations;
- GitHub synchronization.

The next capability must let a user describe a backlog item naturally, identify the intended canonical record, propose a narrow mutation, require confirmation, and invoke the existing mutation path.

Johnny-Johnny is broader than a backlog-only assistant. Future routes may include personal context, email, documents, calendar, and home automation. Therefore every assistant message must not be sent through backlog retrieval by default.

## Decision

### Model-Based Routing Before Domain Retrieval

Every authenticated assistant request first goes through a model-based intent classification step.

The initial routes are:

```text
general_chat
backlog
```

The classifier receives the complete user message and routing instructions. Application code does not perform keyword matching such as checking for `story`, `issue`, or `backlog`.

Application code accepts only a known route value and selects the programmed workflow. Invalid classifier output fails safely.

### Authentication Context Stays Inside Orchestration

The assistant orchestration request carries a safe application principal:

```text
subject
scopes
client_id
```

The principal is retained for workflow ownership and authorization. It is stripped before provider requests. Raw access tokens, claims, and scopes are not sent to the language-model provider.

A future `conversation_id` is included in the orchestration contract so chat memory can be added without replacing the request model.

### Direct Application Use-Case Invocation

Assistant workflows invoke Johnny-Johnny application capabilities directly. They do not make REST calls back into Johnny-Johnny.

```text
external client → REST endpoint → application use case
assistant workflow → same application use case
```

This preserves one implementation of canonical backlog mutation and GitHub synchronization.

### Domain-Specific Retrieval Persistence

Physical retrieval tables remain domain-specific:

```text
backlog_item_embeddings
personal_memory_embeddings          future
project_document_chunks             future
```

A shared provider-neutral embedding and retrieval interface may be reused across domains. A generic “everything” vector table is not introduced prematurely.

Calendar operations will primarily use structured calendar queries and provider APIs rather than the backlog vector table.

### One Current Embedding Per Backlog Item

Each canonical backlog item has at most one current embedding row.

```text
backlog_items.id
    → backlog_item_embeddings.backlog_item_id
```

The embedding row is derived state, not canonical state. It is replaced when its descriptive source changes and deleted automatically when the canonical item is deleted.

Embedding history, chunking, and simultaneous models are deferred until a demonstrated need exists.

### Retrieval Document Contents

Epics and issues are both embedded.

Epic documents include:

- item type;
- title;
- canonical ID;
- description;
- acceptance criteria.

Issue documents additionally include:

- parent epic title;
- parent epic canonical ID.

The first version excludes:

- status;
- comments;
- labels;
- assignees;
- order;
- GitHub identifiers and URLs;
- provider metadata.

Operational fields are loaded from canonical PostgreSQL records after vector retrieval. A status-only change therefore does not require re-embedding.

### Embedding Configuration

The initial embedding configuration is:

```text
model: text-embedding-3-small
dimensions: 1536
distance strategy: cosine
```

The model and dimensions are runtime configuration. Changing the source text, model, or dimensions marks a row stale and triggers regeneration.

### Exact Search First

No HNSW or IVFFlat approximate vector index is added initially. The backlog contains only a few hundred items, so exact vector comparison is simpler and provides exact nearest-neighbor ordering.

An approximate index may be added after measurement demonstrates a need.

## Consequences

### Positive

- General conversation is not polluted by irrelevant backlog retrieval.
- Authorization remains application-owned.
- The model interprets language but cannot grant permission or mutate state directly.
- Existing canonical mutation and GitHub synchronization behavior remains reusable.
- The vector index can be rebuilt without changing canonical backlog data.
- Calendar, personal context, and other capabilities can be added without redesigning backlog storage.
- Status changes avoid unnecessary embedding API calls.

### Tradeoffs

- General chat currently uses two model calls: classification and response generation.
- A classifier can return an invalid result; the application must reject it safely.
- Full chat memory and workflow checkpoint persistence are still required before natural multi-turn confirmation.
- A document recipe or model change requires a full embedding rebuild.
- Domain-specific tables create more physical tables, but preserve explicit ownership and lifecycle rules.

## Alternatives Considered

### Retrieve Backlog Candidates for Every Message

Rejected because nearest-neighbor search always returns something, including for unrelated general-chat requests.

### Keyword Routing in Application Code

Rejected because natural language can express backlog intent without using fixed vocabulary.

### One Generic Vector Table for All Future Domains

Deferred because backlog, personal memory, project documents, email, and calendar have different canonical sources, authorization rules, refresh behavior, and deletion semantics.

### Include Status and Comments in the First Embedding Document

Deferred because they change frequently and are not central to story identity. They remain available after canonical reload and may be added later if retrieval evaluation demonstrates value.

## Implementation Checkpoint

Validated during this session:

- authenticated principal passed into assistant orchestration;
- principal excluded from provider request;
- model-based routing;
- general-chat end-to-end behavior;
- backlog-route deterministic placeholder;
- deterministic retrieval-document generation;
- SHA-256 source hashing;
- OpenAI embedding provider;
- real 1,536-dimension embedding generation;
- PostgreSQL embedding table migration;
- embedding persistence repository unit tests;
- refresh decision unit tests.
