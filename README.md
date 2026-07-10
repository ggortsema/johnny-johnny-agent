# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for Johnny-Johnny, a personal engineering assistant built around deterministic, reusable engineering workflows.

The CLI and FastAPI server are peer adapters over the same application workflows and canonical domain model.

## Current Architecture

```text
CLI ────────────────┐
REST API ───────────┼── application workflows ── canonical domain
webhooks later ─────┘            │
                                 ├── PostgreSQL canonical store
                                 └── provider adapters (GitHub first)
```

PostgreSQL is the canonical runtime store for backlog state. GitHub Projects are provider projections. YAML is a portable import/export, migration, backup, validation, and inspection format—not a runtime intermediary.

Stable Johnny-Johnny IDs are canonical identity. GitHub issue numbers, node IDs, URLs, and project-item IDs are provider metadata.

## Configuration

Place runtime configuration in the project-root `.env` file:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
GITHUB_TOKEN=github-token-with-required-project-and-issue-permissions

# Optional; defaults to the current CLI-compatible account.
JOHNNY_JOHNNY_PROVIDER_ACCOUNT=ggortsema
```

Then install/synchronize dependencies and verify persistence:

```bash
uv sync
uv run jj backlog db check
```

`DATABASE_URL` is server-owned configuration. REST clients cannot submit or override it.

## Start the REST API

The default host is loopback-only because the current server does not yet include authentication middleware.

```bash
uv run jj serve --host 127.0.0.1 --port 8000
```

For a future container or EKS deployment, bind the process to the pod network interface:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

`0.0.0.0` makes the process reachable through the pod network; it is not an authentication control. Do not expose the current unauthenticated API publicly. The next planned story adds OAuth/OIDC authentication and authorization before EKS deployment.

API resources:

```text
Swagger UI:  http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
OpenAPI:     http://127.0.0.1:8000/openapi.json
Base path:   http://127.0.0.1:8000/api/v1
```

## REST API Conventions

Backlog routes select canonical state using:

```text
provider / provider account / stored project title
```

The stored provider-project row supplies the GitHub Project ID. The API never searches by title and silently rebinds the project.

Every mutation requires an explicit mode:

```json
{"mode": "dry-run"}
```

or:

```json
{"mode": "confirmed"}
```

`dry-run` calls the shared preview workflow and changes neither PostgreSQL nor GitHub. `confirmed` calls the same committing workflow used by the CLI. Confirmed create, update, move, and delete operations synchronize the targeted GitHub projection before reporting success.

Errors use one response shape:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Backlog item not found: missing-item",
    "details": null
  }
}
```

See `docs/api/backlog-rest-api.md` for the complete endpoint and error contract.

# Complete Curl Walkthrough

The following sequence exercises every v1 endpoint. Use a disposable or explicitly designated sandbox project for confirmed mutations, especially import, purge, and full reconciliation.

Open a second terminal after starting the server and set these values:

```bash
export API='http://127.0.0.1:8000/api/v1'
export PROVIDER_ACCOUNT='ggortsema'

# URL-encoded stored provider project title.
export PROJECT_PATH='Johnny-Johnny%20Backlog%20Persistence%20Sandbox'

# Repository used for the smoke-test epic and issue.
export REPOSITORY='ggortsema/johnny-johnny-agent'

# An existing canonical item used by the initial describe example.
export EXISTING_ITEM_ID='design-canonical-backlog-persistence'

export LOCATION_QUERY="provider=github&provider_account=${PROVIDER_ACCOUNT}"
```

Replace the values to match the selected canonical project and repository.

## 1. Health and OpenAPI

Process liveness:

```bash
curl -fsS "${API}/health/live" | python3 -m json.tool
```

PostgreSQL and canonical schema readiness:

```bash
curl -fsS "${API}/health/ready" | python3 -m json.tool
```

Download the generated OpenAPI contract:

```bash
curl -fsS 'http://127.0.0.1:8000/openapi.json' \
  -o /tmp/johnny-johnny-openapi.json
```

## 2. PostgreSQL-Backed Reads

Inspect aggregate counts:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/summary?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List epics:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/epics?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List all issues:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/items?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List everything except Done:

```bash
curl -fsS -G \
  "${API}/backlogs/${PROJECT_PATH}/items" \
  --data-urlencode 'provider=github' \
  --data-urlencode "provider_account=${PROVIDER_ACCOUNT}" \
  --data-urlencode 'exclude_status=Done' \
  | python3 -m json.tool
```

Describe one canonical item:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/items/${EXISTING_ITEM_ID}?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

## 3. Create Two Smoke-Test Epics

Preview the source epic:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/epics?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | python3 -m json.tool
{
  "mode": "dry-run",
  "id": "rest-api-smoke-source",
  "title": "REST API Smoke Source",
  "repository": "${REPOSITORY}",
  "description": "Source epic for REST API smoke testing.",
  "acceptance_criteria": [
    "The epic can be previewed and created through REST."
  ]
}
JSON
```

Confirm the source epic:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/epics?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | python3 -m json.tool
{
  "mode": "confirmed",
  "id": "rest-api-smoke-source",
  "title": "REST API Smoke Source",
  "repository": "${REPOSITORY}",
  "description": "Source epic for REST API smoke testing.",
  "acceptance_criteria": [
    "The epic can be previewed and created through REST."
  ]
}
JSON
```

Create the target epic used by the move workflow:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/epics?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | python3 -m json.tool
{
  "mode": "confirmed",
  "id": "rest-api-smoke-target",
  "title": "REST API Smoke Target",
  "repository": "${REPOSITORY}",
  "description": "Target epic for REST API move testing.",
  "acceptance_criteria": []
}
JSON
```

Identical confirmed epic creation is idempotent: it confirms or repairs the existing targeted provider projection rather than inserting a duplicate.

## 4. Create a Smoke-Test Issue

Preview issue creation:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/issues?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | python3 -m json.tool
{
  "mode": "dry-run",
  "id": "rest-api-smoke-issue",
  "parent_epic_id": "rest-api-smoke-source",
  "title": "REST API Smoke Issue",
  "repository": "${REPOSITORY}",
  "description": "Issue used to exercise the REST mutation surface.",
  "acceptance_criteria": [
    "The issue is created in PostgreSQL and projected to GitHub."
  ]
}
JSON
```

Confirm issue creation:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/issues?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | python3 -m json.tool
{
  "mode": "confirmed",
  "id": "rest-api-smoke-issue",
  "parent_epic_id": "rest-api-smoke-source",
  "title": "REST API Smoke Issue",
  "repository": "${REPOSITORY}",
  "description": "Issue used to exercise the REST mutation surface.",
  "acceptance_criteria": [
    "The issue is created in PostgreSQL and projected to GitHub."
  ]
}
JSON
```

List only issues under the source epic:

```bash
curl -fsS -G \
  "${API}/backlogs/${PROJECT_PATH}/items" \
  --data-urlencode 'provider=github' \
  --data-urlencode "provider_account=${PROVIDER_ACCOUNT}" \
  --data-urlencode 'epic_id=rest-api-smoke-source' \
  | python3 -m json.tool
```

## 5. Update the Issue

Preview a status, description, acceptance-criteria, and comment update:

```bash
curl -fsS -X PATCH \
  "${API}/backlogs/${PROJECT_PATH}/items/rest-api-smoke-issue?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "status": "In Progress",
  "description": "Updated through the REST API.",
  "acceptance_criteria": [
    "The canonical update is persisted.",
    "The targeted GitHub projection is synchronized."
  ],
  "comment": "REST API smoke-test update preview."
}
JSON
```

Confirm the update:

```bash
curl -fsS -X PATCH \
  "${API}/backlogs/${PROJECT_PATH}/items/rest-api-smoke-issue?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "confirmed",
  "status": "In Progress",
  "description": "Updated through the REST API.",
  "acceptance_criteria": [
    "The canonical update is persisted.",
    "The targeted GitHub projection is synchronized."
  ],
  "comment": "REST API smoke-test update confirmed."
}
JSON
```

Describe the updated issue:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/items/rest-api-smoke-issue?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

## 6. Move the Issue

Preview the move:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue/move?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "target_epic_id": "rest-api-smoke-target"
}
JSON
```

Confirm the move:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue/move?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "confirmed",
  "target_epic_id": "rest-api-smoke-target"
}
JSON
```

## 7. Reconcile the Provider Projection

Preview a bounded reconciliation chunk:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "max_operations": 100
}
JSON
```

Execute the complete current plan:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "confirmed",
  "all": true
}
JSON
```

A clean projection returns zero selected operations on the next dry run.

## 8. Export and Re-import the Canonical Snapshot

Export portable YAML:

```bash
curl -fsS \
  "${API}/backlogs/${PROJECT_PATH}/export?${LOCATION_QUERY}" \
  -o /tmp/johnny-johnny-backlog.yml

head -40 /tmp/johnny-johnny-backlog.yml
```

Preview importing that same snapshot. The dry run parses and summarizes YAML without connecting to PostgreSQL:

```bash
curl -fsS -X POST \
  "${API}/backlogs/import?mode=dry-run&provider_account=${PROVIDER_ACCOUNT}&verify=true" \
  -H 'Content-Type: application/yaml' \
  --data-binary @/tmp/johnny-johnny-backlog.yml \
  | python3 -m json.tool
```

Confirm the verified transactional snapshot replacement:

```bash
curl -fsS -X POST \
  "${API}/backlogs/import?mode=confirmed&provider_account=${PROVIDER_ACCOUNT}&verify=true" \
  -H 'Content-Type: application/yaml' \
  --data-binary @/tmp/johnny-johnny-backlog.yml \
  | python3 -m json.tool
```

Confirmed import replaces the selected canonical project snapshot. Use only an inspected export or another trusted canonical backlog document.

## 9. Delete the Smoke-Test Issue

Preview deletion:

```bash
curl -fsS -X DELETE \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue?mode=dry-run&${LOCATION_QUERY}" \
  | python3 -m json.tool
```

Confirm deletion from PostgreSQL and the targeted GitHub projection:

```bash
curl -fsS -X DELETE \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue?mode=confirmed&${LOCATION_QUERY}" \
  | python3 -m json.tool
```

The API currently deletes issues, not epics. The two smoke-test epics remain as canonical records unless removed through a future epic-deletion workflow or a controlled snapshot import.

## 10. Purge and Recreate the Entire Sandbox Projection

**These commands delete every Johnny-Johnny-managed GitHub issue in the selected provider projection. Canonical PostgreSQL data is retained. Run them only against a disposable or explicitly approved sandbox.**

Preview the next bounded purge chunk:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/purge?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "max_issues": 50
}
JSON
```

Confirm a full sandbox purge:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/purge?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "confirmed",
  "all": true
}
JSON
```

Preview full recreation from PostgreSQL:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "all": true
}
JSON
```

Recreate the full provider projection:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "confirmed",
  "all": true
}
JSON
```

Verify the recreation is complete:

```bash
curl -fsS -X POST \
  "${API}/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "all": true
}
JSON
```

Expected clean result:

```json
{
  "execution_operation_count": 0,
  "remaining_operation_count": 0,
  "complete": true
}
```

# CLI Reference

The REST API does not replace the CLI. Both call the same application workflows.

## PostgreSQL-Backed Reads

```bash
uv run jj backlog inspect --project "PROJECT"
uv run jj backlog list epics --project "PROJECT"
uv run jj backlog list items --project "PROJECT"
uv run jj backlog describe ITEM_ID --project "PROJECT"
```

List and describe commands support their documented human, YAML, and JSON output formats. YAML output is rendering only.

## Targeted Mutations

```bash
uv run jj backlog create epic ... --project "PROJECT" --dry-run
uv run jj backlog create epic ... --project "PROJECT" --confirm

uv run jj backlog create issue ... --project "PROJECT" --dry-run
uv run jj backlog create issue ... --project "PROJECT" --confirm

uv run jj backlog update ITEM_ID ... --project "PROJECT" --dry-run
uv run jj backlog update ITEM_ID ... --project "PROJECT" --confirm

uv run jj backlog move ISSUE_ID --to-epic EPIC_ID --project "PROJECT" --dry-run
uv run jj backlog move ISSUE_ID --to-epic EPIC_ID --project "PROJECT" --confirm

uv run jj maintenance delete-issue ISSUE_ID --project "PROJECT" --dry-run
uv run jj maintenance delete-issue ISSUE_ID --project "PROJECT" --confirm
```

Confirmed mutations write PostgreSQL and synchronize the targeted GitHub projection before reporting success. Workflows use rollback, compensation, and idempotent repair because PostgreSQL and GitHub cannot share one transaction.

## Reconcile and Purge

```bash
uv run jj backlog reconcile --project "PROJECT" --max-operations 100 --dry-run
uv run jj backlog reconcile --project "PROJECT" --all --confirm

uv run jj maintenance purge --project "PROJECT" --max-issues 50 --dry-run
uv run jj maintenance purge --project "PROJECT" --all --confirm
```

Reconcile reads PostgreSQL and applies the provider plan. Purge removes the GitHub projection while preserving canonical PostgreSQL rows.

## YAML Utilities

```bash
uv run jj backlog validate --file backlog.yml
uv run jj backlog db import --file backlog.yml --dry-run
uv run jj backlog db import --file backlog.yml --confirm
uv run jj backlog db export --project "PROJECT" --output backlog.yml
```

`jj backlog pull` remains a raw GitHub diagnostic.

`jj backlog generate` remains temporarily as a GitHub-to-YAML migration utility and is explicitly deferred for replacement by a direct GitHub-to-PostgreSQL import workflow.

Removed legacy commands:

```text
jj backlog publish
jj backlog preview-epic-body
```

## Tests

Run the full behavior suite:

```bash
uv run pytest
```

The current implementation includes endpoint behavior coverage for every REST v1 path, CLI parity, PostgreSQL persistence, targeted synchronization, reconciliation, and purge.

## Documentation

Start with:

- `docs/api/backlog-rest-api.md`
- `docs/development/rest-api-implementation-summary-2026-07-10.md`
- `docs/architecture/canonical-backlog-runtime-architecture.md`
- `docs/architecture/adrs/ADR-001-postgresql-canonical-backlog-runtime.md`
- `docs/architecture/adrs/ADR-002-targeted-provider-synchronization.md`
- `docs/architecture/adrs/ADR-003-rest-api-is-a-peer-adapter.md`
- `docs/database/postgres/README.md`
- `docs/specifications/backlog-v1.md`
- `docs/development/ENGINEERING_PRINCIPLES.md`
- `docs/development/WORKING_AGREEMENT.md`
