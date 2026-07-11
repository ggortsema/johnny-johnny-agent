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

Historical persistence-story suite at closure:

```text
70 passed, 1 skipped
```

The later REST and Auth0 security stories extended the same applied behavior suite to:

```text
109 passed, 1 skipped
```

The current result includes the original persistence/provider coverage plus REST endpoint dispatch, Auth0 JWT validation, and read/write/operate/admin authorization behavior.

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

The persistence migration's full CLI reconciliation and clean follow-up were confirmed in the later REST session. Live REST purge and reconciliation remain intentionally deferred because they are broad or destructive provider operations; their HTTP dispatch and response behavior are covered by automated tests.

## REST Endpoint Coverage

The server-mode pass now mirrors the workflows through FastAPI:

```text
HTTP request
  -> Auth0 bearer validation
  -> route scope authorization
  -> shared application workflow
  -> PostgreSQL/provider fakes or controlled sandbox
  -> response and side-effect assertions
```

Endpoint tests do not invoke the CLI process. CLI and REST remain peer adapters over shared workflows. The route suite verifies every v1 backlog operation, dry-run and confirmed dispatch, stable errors, public minimal probes, and the read/write/operate/admin authorization policy.
