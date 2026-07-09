# ADR: PostgreSQL as Canonical Persistence

## Status
Accepted

## Context
Johnny-Johnny currently persists its canonical backlog as `backlog.yml`.

Future capabilities including webhooks, chat workflows, audit history, synchronization, and long-running services require a durable runtime store.

## Decision
PostgreSQL will become the canonical runtime persistence mechanism.

`backlog.yml` becomes a portable import/export and human-readable exchange format.

## Consequences
- Runtime reads/writes target PostgreSQL.
- Import/export preserves portability.
- CLI behavior remains stable while persistence changes.
- Provider synchronization operates from canonical database records.
