# Durable Reconciliation Execution Model

**Status:** Partially implemented; durable ledger remains planned  
**Last Updated:** July 10, 2026  
**Project:** Johnny-Johnny Agent

## Purpose

Describe both the reconciliation behavior implemented today and the durable execution model still required for server-mode, provider-rate-aware operation.

## Implemented Baseline

Reconciliation now reads canonical state directly from PostgreSQL and compares it with the provider project bound in `provider_projects`. YAML is not involved.

The command supports:

```bash
jj backlog reconcile --project "..." --dry-run
jj backlog reconcile --project "..." --max-operations 100 --confirm
jj backlog reconcile --project "..." --all --confirm
```

`--max-operations` counts provider operations, not issues. One item can require multiple operations:

```text
create issue
add issue to project
set status
attach issue to epic
create each comment
```

Acceptance criteria are rendered in the issue body and are not individual operations.

The operation budget is soft at item-group boundaries: Johnny-Johnny does not intentionally split one item's operation chain merely to hit the exact numeric limit.

## Current Resume Behavior

If a run stops halfway:

1. Fully completed item groups remain in GitHub and their provider metadata remains in PostgreSQL.
2. The failing group attempts compensation where supported.
3. The command reports failure rather than claiming success.
4. A rerun reloads PostgreSQL and live provider state, rebuilds the plan, skips completed work, and continues.

This is resumable by recalculation. It is not yet a persisted execution ledger.

## Purge Baseline

Provider purge supports bounded and full modes:

```bash
jj maintenance purge --project "..." --max-issues 50 --confirm
jj maintenance purge --project "..." --all --confirm
```

Purge deletes Johnny-Johnny-managed GitHub issues but preserves canonical backlog rows. Provider metadata remains until the final chunk completes, then it is cleared to support deterministic recreation.

## Remaining Problem

GitHub content-generation limits can still stop large full projections. The current CLI does not persist run/operation state, wait on provider retry windows, or execute through a worker queue.

Server mode and webhooks require a durable model that survives process termination and supports observability.

## Target Durable Model

### Reconcile Run

A requested reconciliation with lifecycle state:

```text
planned
running
paused
failed
completed
cancelled
```

### Reconcile Operation

A stable provider-facing or metadata-facing step with:

- stable operation key
- sequence and item group
- operation type
- canonical item/comment identity
- payload JSON
- status and attempt count
- last error and next-attempt time
- provider result JSON

Conceptual tables:

```text
reconcile_runs
reconcile_operations
```

The database is the execution ledger. A future queue dispatches work but is not the source of truth.

```text
PostgreSQL = durable plan and result ledger
Queue      = dispatch
Worker     = provider execution
```

## Rate and Failure Handling

Provider adapters/workers should support:

- content-mutation budgets
- retry-after scheduling
- exponential backoff
- pause rather than crash on throttling
- idempotency recovery by canonical hidden metadata
- retry, cancel, and manual-review states

## Future API Shape

```text
POST /reconcile-runs
GET  /reconcile-runs/{id}
POST /reconcile-runs/{id}/resume
POST /reconcile-runs/{id}/retry-failed
POST /reconcile-runs/{id}/cancel
```

The initial REST pass may expose the existing synchronous workflow, but it must reuse application services and preserve a path toward this durable run model.

## Next Recommendation

After exposing current workflows through REST, implement persisted reconciliation runs and operations before relying on unattended production-scale provider recreation.
