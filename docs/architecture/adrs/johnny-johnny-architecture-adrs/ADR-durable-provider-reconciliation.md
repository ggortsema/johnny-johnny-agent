# ADR: Treat Provider Reconciliation as Durable Orchestration

**Status:** Proposed  
**Date:** July 9, 2026  
**Project:** Johnny-Johnny Agent

## Context

Johnny-Johnny reconciles backlog state against external project-management providers such as GitHub Projects and, eventually, Jira, Linear, GitLab, or other systems.

Early reconciliation treated provider synchronization like a synchronous command:

```text
load canonical backlog
plan provider operations
execute all operations immediately
save hydrated metadata
```

This worked while the operation count was small. It became fragile once reconciliation included:

- creating GitHub issues
- adding issues to GitHub Projects
- setting project statuses
- attaching sub-issues to epics
- creating issue comments
- hydrating provider metadata back into YAML

A full project recreate can now generate hundreds of provider mutations. During main projection recreation, GitHub began returning a null `createIssue` payload after repeated content-generating operations. The retry then failed on the first issue creation, indicating provider-side throttling or secondary rate limiting.

This showed that reconciliation is not a simple command execution problem. It is a durable orchestration problem across an unreliable provider boundary.

## Decision

Johnny-Johnny will treat provider reconciliation as durable orchestration, not as a single synchronous command.

A reconcile request should create a durable reconcile run and a sequence of durable reconcile operations. Provider mutations should be executed by an executor that can apply rate limits, persist progress, retry failures, pause safely, and resume later.

The database is the durable ledger of intent and execution state. A message queue may be used to dispatch work, but the queue is not the source of truth.

## Rationale

When work stays inside one process, a command or runlist can be enough.

When work crosses a provider boundary, the external system may:

- accept the request
- reject the request
- partially apply the request
- throttle the caller
- return an ambiguous result
- succeed while the local process crashes before recording success
- later drift from the requested state

Therefore, provider synchronization needs orchestration semantics:

- ordered operations
- durable execution state
- idempotency keys
- retry/backoff
- provider rate limits
- failure routing
- pause/resume
- audit history
- reconciliation after partial success

## Consequences

### Positive

- Large reconciliations can be resumed instead of restarted.
- GitHub/Jira throttling can be handled without corrupting state.
- Provider mutation failures become visible and inspectable.
- Reconciliation gains an audit trail.
- The CLI, API, and future workers can share the same execution model.
- This aligns Johnny-Johnny with StyxCD's broader orchestration model.

### Negative

- Reconciliation becomes more complex than a synchronous CLI function.
- The database schema must include reconcile run/operation state.
- Execution requires idempotency and provider-specific recovery logic.
- Messaging or background execution becomes desirable sooner than originally planned.

## Implementation Direction

Introduce durable reconcile execution tables:

```text
reconcile_runs
reconcile_operations
```

The command:

```bash
jj backlog reconcile --file data/input/backlog/backlog.yml --confirm
```

should eventually:

1. Load canonical backlog.
2. Read provider state.
3. Build a reconcile plan.
4. Persist a reconcile run.
5. Persist ordered reconcile operations.
6. Execute operations through a rate-limited executor.
7. Mark each operation as succeeded, failed, skipped, or pending retry.
8. Save/hydrate provider metadata as operations complete.
9. Allow resume/retry by command or API.

Potential commands:

```bash
jj backlog reconcile status <run-id>
jj backlog reconcile resume <run-id>
jj backlog reconcile retry-failed <run-id>
```

Potential API endpoints:

```text
POST /reconcile-runs
GET  /reconcile-runs/{id}
POST /reconcile-runs/{id}/resume
POST /reconcile-runs/{id}/retry-failed
POST /reconcile-runs/{id}/cancel
```

## Guiding Principle

If the work is internal to Johnny-Johnny, a command may be enough.

If the work crosses a system boundary, Johnny-Johnny is orchestrating.
