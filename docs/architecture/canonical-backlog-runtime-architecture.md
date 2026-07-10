# Canonical Backlog Runtime Architecture

**Status:** Implemented baseline  
**Date:** July 10, 2026

## Purpose

Describe the runtime architecture after migrating Johnny-Johnny backlog commands from YAML-backed state to PostgreSQL-backed canonical persistence.

## Runtime Shape

```text
CLI today ───────────┐
REST API next ───────┼── application workflows ── canonical domain
webhooks later ──────┘            │
                                  ├── PostgreSQL repository
                                  └── provider adapters (GitHub first)
```

Presentation adapters must reuse application workflows. The REST server must not shell out to CLI commands.

## Canonical Read Path

```text
provider/account/project title
  -> provider_projects lookup
  -> load backlog_items and child records
  -> reconstruct Backlog domain model
  -> render human, YAML, or JSON output
```

Implemented PostgreSQL reads:

```text
jj backlog inspect
jj backlog list epics
jj backlog list items
jj backlog describe
```

Output formats are presentation choices. Selecting YAML output does not make YAML part of the persistence path.

## Targeted Mutation Path

```text
request
  -> validate/preview domain mutation
  -> lock stored provider project in PostgreSQL transaction
  -> mutate canonical records
  -> apply targeted GitHub projection changes
  -> hydrate provider metadata
  -> commit
```

Implemented mutations:

```text
jj backlog create epic
jj backlog create issue
jj backlog update
jj backlog move
jj maintenance delete-issue
```

See ADR-002 for failure and compensation behavior.

## Full Projection Workflows

### Reconcile

`jj backlog reconcile` compares PostgreSQL canonical state with the bound GitHub Project and executes a provider plan.

- Default bounded scope: 100 provider operations.
- `--max-operations N`: soft budget; complete item groups are not intentionally split.
- `--all`: execute the complete currently planned scope.
- A rerun reads live state, rebuilds the plan, and skips completed work.

An operation means a provider action, not an issue. One item may require create, add-to-project, status, parent, and comment operations. Acceptance criteria are rendered inside the issue body.

### Purge

`jj maintenance purge` deletes Johnny-Johnny-managed GitHub issues while preserving canonical PostgreSQL state.

- Default bounded scope: 50 issues.
- `--max-issues N`: bounded provider deletion.
- `--all`: attempt the full current projection.
- Canonical provider metadata remains until the final purge chunk completes, then it is cleared to support recreation.

## Portable YAML Boundary

Intentionally file-oriented commands:

```text
jj backlog validate
jj backlog db import
jj backlog db export
```

`jj backlog generate` remains temporarily as a GitHub-to-YAML migration utility. It is explicitly deferred for replacement by a renamed GitHub-to-PostgreSQL import workflow after durable provider execution is implemented.

`jj backlog pull` remains a raw GitHub diagnostic.

Removed legacy commands:

```text
jj backlog publish
jj backlog preview-epic-body
```

## Provider Project Binding

The command option `--project` identifies the stored `provider_projects` row. The row's external ID determines the GitHub Project target.

Runtime reconciliation does not search GitHub by title and silently rewrite the binding. Rebinding must be an explicit future capability.

## Next Evolution

Expose the same workflows through FastAPI endpoints with:

- typed request/response models
- consistent domain error mapping
- dry-run and confirmation semantics
- no duplicated business logic
- endpoint behavior tests mirroring CLI behavior tests

Later evolutions add webhook ingestion, durable reconcile runs/operations, rate-aware workers, and audit history.
