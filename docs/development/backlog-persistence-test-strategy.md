# Backlog Persistence and Provider Synchronization Test Strategy

**Date:** July 10, 2026

## Goal

Prove that PostgreSQL-backed commands preserve canonical domain behavior and keep targeted GitHub projections consistent without using YAML as a runtime intermediary.

## Automated Behavior Coverage

The behavior suite covers:

- PostgreSQL readiness, import, export, and semantic round trips
- database-backed inspect/list/describe commands
- CLI grammar after intentional breaking changes
- targeted epic and issue creation
- idempotent create repair and conflicting-create rejection
- title, description, acceptance-criteria, status, and comment updates
- issue moves and parent restoration on failure
- targeted delete retry behavior
- bounded and full reconcile selection
- purge behavior that preserves canonical rows
- provider compensation and explicit consistency errors
- proof that migrated commands do not call the YAML loader

Validated suite at closure:

```text
70 passed, 1 skipped
```

## Live Sandbox Validation

Manually validated against:

```text
GitHub Project: Johnny-Johnny Backlog Persistence Sandbox
PostgreSQL database: styxcd
Schema: johnny_johnny
```

Validated live behaviors:

- database connectivity and schema readiness
- YAML snapshot import and semantic export round trip
- database-backed read commands and output formats
- targeted epic creation and idempotent repair
- targeted issue creation
- status and comment update
- title, description, and acceptance-criteria update
- issue move between epics
- targeted issue deletion dry run
- full provider purge while retaining canonical data
- full reconciliation launched from PostgreSQL after purge

The final full-reconcile completion and zero-operation follow-up were not confirmed before session closure and remain the first verification step next session.

## REST Endpoint Testing Requirement

The next server-mode pass should mirror each workflow test through FastAPI:

```text
HTTP request
  -> application workflow
  -> PostgreSQL/provider fakes or controlled sandbox
  -> response and side-effect assertions
```

Endpoint tests must not invoke the CLI process. CLI and REST are peer adapters over shared workflows.
