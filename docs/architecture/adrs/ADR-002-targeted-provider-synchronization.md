# ADR-002: Targeted Provider Synchronization for Canonical Mutations

**Status:** Accepted  
**Date:** July 10, 2026  
**Story:** `design-canonical-backlog-persistence`

## Context

A user who runs `create epic`, `create issue`, `update`, `move`, or `delete-issue` expects the corresponding GitHub projection to reflect the change before the command reports success.

PostgreSQL and GitHub cannot participate in one ACID transaction. A workflow can fail after either side has changed, so consistency must be managed explicitly.

Full-project reconciliation is not appropriate for a single mutation and can trigger GitHub content-generation limits.

## Decision

Confirmed canonical mutations use a targeted cross-boundary workflow:

```text
open and lock PostgreSQL transaction
  -> apply canonical mutation without committing
  -> perform only the required GitHub mutation(s)
  -> hydrate returned provider metadata
  -> commit PostgreSQL
  -> report success
```

The public operation succeeds only when canonical state and the targeted provider projection are complete.

### Failure behavior

- If GitHub fails before completion, PostgreSQL rolls back.
- If GitHub succeeds but PostgreSQL finalization fails, Johnny-Johnny attempts compensating GitHub mutations.
- If compensation fails, Johnny-Johnny reports the possible orphan or partial state explicitly.
- A retry is idempotent and uses canonical IDs plus hidden Johnny-Johnny metadata to reuse or repair an existing provider item.
- Repeating `create` with the same canonical ID and identical canonical content repairs or confirms projection state.
- Repeating `create` with conflicting canonical content is rejected; callers must use `update` or `move`.

### Command-specific semantics

- `create epic` creates the canonical epic, GitHub issue, project membership, status, and provider metadata.
- `create issue` additionally attaches the GitHub issue beneath its parent epic.
- `update` changes canonical content/status/comments and applies targeted provider changes.
- `move` changes only parent hierarchy and ordering; it does not silently change repository or milestone.
- `delete-issue` deletes both the GitHub issue and canonical issue and is safe to retry when the provider issue is already absent.
- `purge` removes the provider projection while preserving canonical PostgreSQL rows. Provider metadata is cleared only after the final purge chunk.

## Reconciliation Scope

Full reconciliation remains a separate recovery and projection workflow. It loads canonical state from PostgreSQL and supports:

- bounded execution with `--max-operations`
- explicit full-plan execution with `--all`
- item-group boundaries so one item's operation chain is not intentionally split
- rerunning after failure to recalculate and continue from provider state

This is resumable-by-recalculation, not yet a durable persisted operation ledger. Durable runs, backoff, and provider throttling remain future work.

## Consequences

### Positive

- Normal user-facing mutations produce the provider result users expect.
- One mutation does not require a full-project reconcile.
- Retry behavior avoids duplicate issues and comments where metadata is recoverable.
- Partial states are surfaced instead of hidden.

### Costs

- Cross-boundary atomicity is simulated, not guaranteed.
- PostgreSQL transactions can remain open during provider calls.
- Compensation logic is provider-specific and must be tested.
- A provider outage may cause a canonical mutation to fail rather than committing a pending intent; a future durable synchronization ledger may change that policy.
