# Backlog Session Update Plan — July 10, 2026

The canonical backlog lives in PostgreSQL. This file records canonical backlog updates that should be applied through Johnny-Johnny rather than by editing YAML.

## Persistence Story Completion Confirmed

The final full sandbox reconciliation completed successfully. A subsequent full dry run reported no remaining work, and the expected projection is present in GitHub.

`design-canonical-backlog-persistence` can remain in Done with the completion comment already applied.

## REST Story Implemented

Story:

```text
ID: expose-backlog-workflows-through-rest-api
Title: Expose Backlog Workflows Through REST API
```

Implemented behavior:

- versioned FastAPI surface under `/api/v1`
- inspect/summary, list epics, list items, and describe endpoints
- create epic, create issue, update, move, and delete issue endpoints
- database readiness, reconcile, purge, YAML import, and YAML export endpoints
- direct reuse of PostgreSQL-backed application workflows; no CLI shell invocation
- strict typed request and response models
- explicit `dry-run` and `confirmed` mutation modes
- consistent validation, not-found, conflict, provider, persistence, and cross-boundary consistency errors
- endpoint behavior coverage for every v1 path
- complete README `curl` walkthrough for exercising the server surface

Suggested canonical completion update:

```bash
uv run jj backlog update \
  expose-backlog-workflows-through-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --status "Done" \
  --comment "Implemented the versioned FastAPI backlog surface with typed models, explicit dry-run/confirmed semantics, shared PostgreSQL-backed workflows, consistent HTTP errors, YAML import/export boundaries, complete endpoint behavior tests, and runnable README curl examples." \
  --confirm
```

Use the correct canonical project title if the engineering backlog is rebound or imported into another provider project.

## Acceptance Criteria Review

- Read endpoints expose inspect, list epics, list items, and describe behavior: **met**.
- Mutation endpoints expose create epic, create issue, update, move, and delete issue behavior: **met**.
- Operational endpoints expose reconcile, purge, database readiness, import, and export where appropriate: **met**.
- REST handlers reuse the same application workflows as the CLI and never shell out to `jj`: **met**.
- Request and response models are typed and stable: **met**.
- Domain, validation, provider, conflict, and consistency errors map to consistent HTTP responses: **met**.
- Dry-run and confirmed mutation semantics are represented explicitly: **met**.
- Behavior tests exercise every endpoint and verify parity with CLI workflows: **met**.
- `jj serve` starts the completed API surface: **met**.

## Recommended Follow-Ups

- Add authentication and authorization before binding the server beyond trusted interfaces.
- Replace and rename `jj backlog generate` as a direct provider-to-PostgreSQL import workflow.
- Persist durable reconciliation runs and operations with retry/backoff and provider throttling.
- Add an explicit provider-project rebind workflow rather than inferring rebinding during reconcile.
- Decide whether long-running server mutations remain synchronous or return durable operation resources.
