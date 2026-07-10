# Canonical Backlog Domain Model

**Status:** Implemented baseline  
**Last Updated:** July 10, 2026

## Purpose

Describe the core backlog domain independently of storage and provider implementation.

## Core Concepts

- User
- Provider
- Provider Account
- Provider Project
- Backlog Item
- Acceptance Criterion
- Comment
- Label
- Assignee

## Hierarchy

```text
User
└── Provider Account
    └── Provider Project
        └── Backlog Item
            ├── Acceptance Criteria
            ├── Comments
            ├── Labels
            └── Assignees
```

Epics and issues share the `Backlog Item` concept. Type and parent hierarchy distinguish them.

## Identity

Canonical IDs are stable semantic identities. A title can change without changing the canonical ID.

Provider identifiers are projection metadata:

```text
GitHub node id
GitHub database id
GitHub issue number
GitHub URL
GitHub project-item id
```

Those values are persisted because provider APIs and diagnostics need them, but they do not define canonical identity. If a provider projection is recreated, provider metadata may change while the canonical ID remains stable.

## Runtime Persistence

- PostgreSQL is the canonical runtime store.
- YAML is an import/export, backup, migration, and inspection format.
- Runtime commands never use YAML as a hidden persistence intermediary.
- Ordering is canonical domain data.
- Repositories identify implementation/projection targets, not backlog identity.

## Provider Project Binding

A canonical project is selected by provider, provider account, and project title. Its database record contains the provider external identity used for synchronization.

Runtime commands do not silently change that binding by searching the provider by title. Rebinding is a separate explicit future capability.

## Consistency

Confirmed mutations are expected to leave canonical state and the required provider projection aligned before reporting success. Because PostgreSQL and providers cannot share an ACID transaction, workflows use idempotency, compensation, and explicit consistency errors.

See:

- `canonical-backlog-domain-model-erd.md`
- `canonical-backlog-db-field-mapping.md`
- `canonical-backlog-runtime-architecture.md`
- `adrs/ADR-001-postgresql-canonical-backlog-runtime.md`
- `adrs/ADR-002-targeted-provider-synchronization.md`
