# Backlog Session Update Plan — July 10, 2026

The canonical backlog now lives in PostgreSQL. This file records the backlog updates that should be applied through Johnny-Johnny rather than editing YAML by hand.

## Complete Current Persistence Story

Update `design-canonical-backlog-persistence` to Done after verifying the final full sandbox reconciliation:

```bash
uv run jj backlog update \
  design-canonical-backlog-persistence \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --status "Done" \
  --comment "Implemented PostgreSQL as the canonical runtime store; migrated backlog reads and mutations; added targeted GitHub synchronization with compensation and idempotent repair; added bounded/all reconcile and purge; validated import/export round trips and live sandbox workflows." \
  --confirm
```

Use the correct canonical project title if the engineering backlog is rebound or imported into a different provider project.

## Create Next Story

Recommended next story under `backlog-as-code-synchronization`:

```text
ID: expose-backlog-workflows-through-rest-api
Title: Expose Backlog Workflows Through REST API
Status: Ready
```

Proposed description:

```text
Expose the PostgreSQL-backed backlog application workflows through FastAPI so every supported CLI capability can also be exercised in server mode without invoking the CLI or duplicating business logic.
```

Proposed acceptance criteria:

- Read endpoints expose inspect, list epics, list items, and describe behavior.
- Mutation endpoints expose create epic, create issue, update, move, and delete issue behavior.
- Operational endpoints expose reconcile, purge, database readiness, import, and export where appropriate.
- REST handlers reuse the same application workflows as the CLI and never shell out to `jj`.
- Request and response models are typed and stable.
- Domain, validation, provider, conflict, and consistency errors map to consistent HTTP responses.
- Dry-run and confirmed mutation semantics are represented explicitly.
- Behavior tests exercise every endpoint and verify parity with CLI workflows.
- `jj serve` starts the completed API surface.

## Deferred Follow-Ups

- Replace and rename `jj backlog generate` as a direct provider-to-PostgreSQL import workflow.
- Persist durable reconciliation runs and operations with retry/backoff and provider throttling.
- Add an explicit provider-project rebind workflow rather than inferring rebinding during reconcile.
