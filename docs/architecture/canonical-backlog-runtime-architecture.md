# Canonical Backlog Runtime Architecture

**Status:** Implemented baseline  
**Date:** July 10, 2026

## Purpose

Describe the runtime architecture after migrating Johnny-Johnny backlog commands from YAML-backed state to PostgreSQL-backed canonical persistence.

## Runtime Shape

```text
CLI ────────────────┐
REST API ───────────┼── application workflows ── canonical domain
webhooks later ────┘            │
                                ├── PostgreSQL repository
                                └── provider adapters (GitHub first)
```

Presentation adapters reuse application workflows. The implemented REST server imports those workflows directly and never shells out to CLI commands.

## REST Adapter Path

```text
HTTP request
  -> typed FastAPI request model
  -> explicit dry-run or confirmed mode
  -> shared PostgreSQL-backed application workflow
  -> typed response model or consistent HTTP error
```

Implemented REST behavior:

- read parity for inspect, list epics, list items, and describe
- targeted mutation parity for create epic, create issue, update, move, and delete issue
- operational parity for database readiness, reconcile, purge, YAML import, and YAML export
- one explicit `mode` contract for previews and confirmed mutations
- server-owned database configuration; clients cannot submit database URLs
- direct YAML request/response handling only at the portable import/export boundary

See `docs/api/backlog-rest-api.md` for the endpoint and error contracts and ADR-003 for the adapter decision.

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

The REST baseline is implemented. Later evolutions add:

- server authentication and authorization before binding beyond trusted interfaces
- webhook ingestion
- durable reconcile runs and operations
- rate-aware workers and asynchronous operation resources where needed
- audit history
- explicit provider-project rebinding
