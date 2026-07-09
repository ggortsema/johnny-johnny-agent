# Durable Reconciliation Execution Model

**Status:** Draft  
**Date:** July 9, 2026  
**Project:** Johnny-Johnny Agent

## Purpose

This document describes the target execution model for provider reconciliation.

The immediate driver is GitHub Project reconciliation. However, the model should support future providers such as Jira, Linear, GitLab, and other project-management systems.

## Problem

The current reconcile command builds an in-memory plan and executes provider operations synchronously.

That model breaks down when a reconciliation produces many provider mutations, such as:

```text
CreateProviderIssue
AddIssueToProject
UpdateProviderStatus
AttachProviderChildIssue
CreateProviderComment
HydrateProviderMetadata
```

A full GitHub projection recreate can exceed provider content-generation limits. When this happens, a synchronous command may fail after partially mutating the provider, leaving the projection dirty and requiring manual recovery.

## Design Goal

Reconciliation should be:

- durable
- observable
- resumable
- rate-limited
- idempotent
- provider-aware
- safe after partial failure

## Core Concepts

### Reconcile Run

A reconcile run represents one requested reconciliation.

Example:

```text
Reconcile the backlog from backlog.yml into the GitHub project "MycroftAI Engineering Roadmap".
```

A run has lifecycle state:

```text
planned
running
paused
failed
completed
cancelled
```

### Reconcile Operation

A reconcile operation is one provider-facing or metadata-facing step.

Examples:

```text
github:create-issue:gke-workflow
github:add-to-project:gke-workflow
github:update-status:gke-workflow
github:attach-sub-issue:implement-gke-deployment-stage
github:create-comment:comment-abc123
```

Each operation should have:

- stable operation identity
- sequence number
- operation type
- target item id
- provider
- payload JSON
- status
- attempt count
- last error
- next attempt time
- provider result JSON

## Database Shape

Initial conceptual schema:

```text
reconcile_runs
  id
  workspace_id
  provider
  provider_project_id
  source_snapshot_id
  source_file_path
  status
  created_at
  started_at
  completed_at
  failure_reason
  created_by

reconcile_operations
  id
  reconcile_run_id
  sequence
  operation_key
  operation_type
  backlog_item_id
  comment_id
  provider
  payload_json
  status
  attempts
  last_error
  next_attempt_at
  provider_result_json
  created_at
  updated_at
```

Operation statuses:

```text
pending
running
succeeded
failed
paused
skipped
cancelled
```

## Queue Role

A message queue may dispatch operation execution.

However, the queue is not the system of record.

```text
Postgres = durable reconcile ledger
Queue    = work dispatch
Executor = provider mutation worker
```

This avoids losing the reconcile plan if a worker, process, or queue message disappears.

## Execution Flow

```text
CLI/API request
  -> load backlog
  -> read provider state
  -> build reconcile plan
  -> persist reconcile_run
  -> persist reconcile_operations
  -> enqueue run or first operation
  -> executor processes operations in order
  -> after each operation, persist result
  -> stop/pause on provider throttle or unrecoverable failure
  -> resume later from pending/failed operations
```

## Rate Limiting

Provider adapters should own provider-specific rate limits.

For GitHub, the executor should avoid treating the API as an unlimited pipe. It should support:

- minimum delay between content mutations
- max operations per run
- max content mutations per time window
- retry-after / next-attempt scheduling
- pause instead of crash when limits are reached

## Idempotency

Every operation should be safe to retry.

Example:

```text
github:create-comment:comment-abc123
```

If the local process crashes after GitHub creates the comment but before Johnny-Johnny saves metadata, resume should:

1. Read provider comments.
2. Find the Johnny-Johnny metadata block for `comment-abc123`.
3. Hydrate provider metadata.
4. Mark the operation as succeeded.
5. Avoid creating a duplicate comment.

## Failure Routing

Failures should not destroy the whole reconcile run.

Possible failure handling:

```text
transient provider failure -> retry with backoff
provider throttle -> pause until next_attempt_at
validation failure -> failed/manual review
idempotency recovery success -> succeeded
unrecoverable provider error -> failed/dead-letter
```

## CLI Shape

Potential commands:

```bash
jj backlog reconcile --file data/input/backlog/backlog.yml --confirm
jj backlog reconcile status <run-id>
jj backlog reconcile resume <run-id>
jj backlog reconcile retry-failed <run-id>
jj backlog reconcile cancel <run-id>
```

Near-term simpler option:

```bash
jj backlog reconcile --file data/input/backlog/backlog.yml --confirm --max-operations 100
```

This can be implemented before full messaging, as long as operations are persisted and resumable.

## API Shape

Potential endpoints:

```text
POST /reconcile-runs
GET  /reconcile-runs/{id}
POST /reconcile-runs/{id}/resume
POST /reconcile-runs/{id}/retry-failed
POST /reconcile-runs/{id}/cancel
```

## Relationship to Canonical Backlog Persistence

The database is not only storage for backlog items. It also becomes the execution ledger for synchronization.

This distinction matters:

```text
backlog tables              = what Johnny-Johnny understands about work
provider projection tables  = how providers represent that work
reconcile tables            = what Johnny-Johnny attempted, succeeded, failed, or needs to resume
```

## Near-Term Recommendation

Before another production-scale destructive recreate, implement at least:

1. provider schema preflight
2. guarded GitHub mutation responses
3. max operation limit or mutation budget
4. persisted reconcile run/operation state
5. resume command

Messaging can follow immediately after, or be introduced once the persisted operation ledger exists.
