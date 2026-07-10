# ADR-001: PostgreSQL Is the Canonical Backlog Runtime Store

**Status:** Accepted  
**Date:** July 10, 2026  
**Story:** `design-canonical-backlog-persistence`

## Context

Johnny-Johnny originally treated `backlog.yml` as the runtime source of truth. That model was useful for bootstrapping the domain and synchronization behavior, but it does not support the next operating model well:

- long-running server processes
- REST and chat interfaces
- provider webhooks
- audit and synchronization history
- concurrent users and workflows
- multiple provider projections

Using YAML inside normal commands would also make the file an implicit intermediary between the domain and PostgreSQL.

## Decision

PostgreSQL is the canonical runtime store for backlog state.

Normal backlog reads and mutations load and persist the canonical domain model directly through the PostgreSQL repository. They must not read or write YAML as an intermediary.

YAML remains supported only as a portable boundary for:

- import and migration
- export and backup
- human inspection
- schema validation

A project supplied to a runtime command is resolved through the stored identity tuple:

```text
provider / provider account / provider project title
```

That database record contains the bound provider identifiers, including the GitHub ProjectV2 ID. Runtime commands do not silently search for and rebind a different provider project by title.

Stable Johnny-Johnny canonical IDs are the domain identity. Provider issue numbers, node IDs, database IDs, URLs, and project-item IDs are persisted as provider metadata and may change without changing canonical identity.

## Consequences

### Positive

- CLI, REST, chat, and webhook adapters can reuse the same application workflows.
- Backlog state is queryable, transactional, and ready for audit/history tables.
- YAML is still portable without controlling runtime behavior.
- Provider bindings are explicit and predictable.
- Renaming an epic or issue does not change its canonical ID.

### Costs

- PostgreSQL configuration is required for normal runtime commands.
- Provider-project metadata must be accurate before provider mutations run.
- Import/export round trips are semantic; YAML mapping-key order is not significant.
- Rebinding a canonical project to a new provider project needs an explicit future workflow.

## Alternatives Rejected

### Keep YAML as the runtime source of truth

Rejected because it creates concurrency, server-mode, webhook, and audit limitations and would keep files inside every command path.

### Support parallel YAML-backed and PostgreSQL-backed commands

Rejected because two runtime paths would create ambiguous behavior and double the compatibility burden. The migration intentionally makes breaking command changes.
