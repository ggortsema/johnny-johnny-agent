# Backlog REST API

**Status:** Implemented v1
**Base path:** `/api/v1`
**Server command:** `uv run jj serve`

## Purpose

The REST API is a peer presentation adapter to the Johnny-Johnny CLI. It calls the same PostgreSQL-backed application workflows directly and never shells out to `jj`.

```text
CLI ─────┐
REST ────┼── application workflows ── canonical domain
         │            │
         │            ├── PostgreSQL canonical store
         │            └── GitHub provider adapter
         └── typed request/response contracts
```

PostgreSQL remains canonical runtime state. GitHub remains a provider projection. YAML appears only at the explicit import/export boundary.

## Runtime Configuration

The server process reads configuration from the environment or project-root `.env` file:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
GITHUB_TOKEN=github-token-with-required-project-and-issue-permissions
JOHNNY_JOHNNY_PROVIDER_ACCOUNT=ggortsema
```

`JOHNNY_JOHNNY_PROVIDER_ACCOUNT` is optional and defaults to `ggortsema` to match the current CLI default.

The API deliberately does not accept a database URL from HTTP clients. Database topology and credentials are server configuration, not request data.

## Starting the Server

```bash
uv sync
uv run jj serve --host 127.0.0.1 --port 8000
```

Interactive contracts are available at:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
http://127.0.0.1:8000/openapi.json
```

The current server has no authentication middleware. Keep it bound to a trusted interface, normally `127.0.0.1`, until server authentication and authorization are implemented.

## Project Selection

Backlog routes identify a project by its stored provider project title in the URL path. The `provider` and `provider_account` query parameters complete the canonical location:

```text
provider / provider account / project title
```

Defaults:

```text
provider=github
provider_account=$JOHNNY_JOHNNY_PROVIDER_ACCOUNT or ggortsema
```

The stored provider project binding supplies the GitHub Project node ID. The API does not search GitHub by title or silently rebind a project.

## Execution Modes

Every mutation requires an explicit execution mode:

```json
{"mode": "dry-run"}
```

or:

```json
{"mode": "confirmed"}
```

`dry-run` calls the corresponding preview workflow and does not change PostgreSQL or GitHub. `confirmed` calls the committing workflow. Create endpoints return HTTP `201` only for confirmed creation; previews return `200`.

Delete and YAML import carry `mode` as a required query parameter because delete has no JSON body and import uses its body for raw YAML.

## Endpoint Inventory

### Health

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/v1/health/live` | Process liveness and API version |
| `GET` | `/api/v1/health/ready` | PostgreSQL connectivity and canonical schema readiness; returns `503` when not ready |

### Reads

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/v1/backlogs/{project_title}/summary` | Project identity and aggregate counts |
| `GET` | `/api/v1/backlogs/{project_title}/epics` | Ordered epic summaries |
| `GET` | `/api/v1/backlogs/{project_title}/items` | Ordered issue summaries with optional epic and status filters |
| `GET` | `/api/v1/backlogs/{project_title}/items/{item_id}` | Full epic or issue detail |

`GET .../items` accepts:

- `epic_id`
- repeated `status`
- repeated `exclude_status`

`status` and `exclude_status` are mutually exclusive, matching the CLI behavior.

### Targeted Mutations

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/backlogs/{project_title}/epics` | Preview or create one canonical epic and targeted GitHub projection |
| `POST` | `/api/v1/backlogs/{project_title}/issues` | Preview or create one canonical issue under an epic |
| `PATCH` | `/api/v1/backlogs/{project_title}/items/{item_id}` | Preview or update title, description, status, acceptance criteria, and/or comment |
| `POST` | `/api/v1/backlogs/{project_title}/issues/{issue_id}/move` | Preview or move an issue to another epic |
| `DELETE` | `/api/v1/backlogs/{project_title}/issues/{issue_id}` | Preview or delete a canonical issue and targeted GitHub projection |

Confirmed targeted mutations report success only after the required GitHub synchronization and canonical PostgreSQL commit succeed. The shared application workflows retain their rollback, compensation, idempotent repair, and explicit consistency-error behavior.

### Projection Operations

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/backlogs/{project_title}/reconciliation` | Preview or execute a bounded/full provider reconciliation |
| `POST` | `/api/v1/backlogs/{project_title}/purge` | Preview or delete a bounded/full GitHub projection while retaining canonical data |

Reconciliation body scope:

```json
{"mode": "dry-run", "max_operations": 100}
```

or:

```json
{"mode": "confirmed", "all": true}
```

Purge body scope:

```json
{"mode": "dry-run", "max_issues": 50}
```

or:

```json
{"mode": "confirmed", "all": true}
```

`all` is mutually exclusive with the corresponding maximum. Omitting both uses the CLI-compatible defaults: 100 provider operations for reconciliation and 50 issues for purge.

### Portable YAML Boundary

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/backlogs/import?mode=...` | Parse or transactionally replace one canonical snapshot from an `application/yaml` body |
| `GET` | `/api/v1/backlogs/{project_title}/export` | Return an `application/yaml` canonical snapshot |

Import dry-run parses and summarizes the document without connecting to PostgreSQL. Confirmed import performs the same verified snapshot replacement used by the CLI.

Export includes count headers:

```text
X-Johnny-Epic-Count
X-Johnny-Issue-Count
X-Johnny-Comment-Count
```

## Error Contract

Errors use one JSON shape:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Backlog item not found: missing-item",
    "details": null
  }
}
```

Status mapping:

| HTTP status | Error category |
|---|---|
| `400` | Invalid cross-field request, such as simultaneous include/exclude filters |
| `404` | Canonical item, epic, issue, or stored provider project not found |
| `409` | Resource conflict, round-trip failure, or cross-boundary consistency failure |
| `422` | Request-model, backlog-document, or domain validation failure |
| `502` | GitHub/provider operation failure |
| `503` | PostgreSQL persistence unavailable or readiness incomplete |
| `500` | Unexpected internal failure without implementation details in the response |

## Test Coverage

`tests/behavior/test_backlog_rest_api.py` exercises every v1 endpoint and verifies:

- PostgreSQL-backed read workflow reuse
- dry-run versus confirmed workflow dispatch
- typed operation serialization
- bounded versus full reconcile and purge scope
- raw YAML import and YAML export
- readiness status behavior
- stable error mapping

The API tests do not require `httpx`; they drive the ASGI application directly through a small dependency-free test client.

## Full Curl Walkthrough

The project README contains a sequential sandbox walkthrough with runnable `curl` commands for every endpoint, including safe previews before confirmed operations.
