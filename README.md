# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for Johnny-Johnny, a personal engineering assistant built around deterministic, reusable engineering workflows.

The CLI and the Auth0-secured FastAPI server are peer adapters over the same application workflows and canonical domain model.

## Current Architecture

```text
CLI ───────────────────────┐
Auth0-secured REST API ────┼── application workflows ── canonical domain
signed webhooks later ─────┘            │
                                        ├── PostgreSQL canonical store
                                        └── provider adapters (GitHub first)
```

PostgreSQL is the canonical runtime store for backlog state. GitHub Projects are provider projections. YAML is a portable import/export, migration, backup, validation, and inspection format—not a runtime intermediary.

Stable Johnny-Johnny IDs are canonical identity. GitHub issue numbers, node IDs, URLs, and project-item IDs are provider metadata.

## Install and Configure

Synchronize the locked Python environment:

```bash
uv sync
```

Copy the committed example and fill in the local values:

```bash
cp .env.example .env
```

The API process uses these settings:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
GITHUB_TOKEN=github-token-with-required-project-and-issue-permissions
JOHNNY_JOHNNY_PROVIDER_ACCOUNT=ggortsema

AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.johnny-johnny.local
JOHNNY_JOHNNY_API_DOCS_ENABLED=true
```

`AUTH0_DOMAIN` and `AUTH0_AUDIENCE` are required when the REST server starts. The API deliberately does **not** need an Auth0 client ID or client secret; those belong to calling applications, not the resource server. `DATABASE_URL` and `GITHUB_TOKEN` are also server-owned and cannot be overridden by an HTTP request.

Verify persistence independently of HTTP authentication:

```bash
uv run jj backlog db check
```

## Configure Auth0

### 1. Create the Johnny-Johnny API

In the Auth0 dashboard:

1. Open **Applications → APIs** and choose **Create API**.
2. Use a name such as `Johnny-Johnny API`.
3. Use a stable identifier such as `https://api.johnny-johnny.local`. This exact value becomes `AUTH0_AUDIENCE`; it does not need to be a publicly reachable URL.
4. Select **RS256** as the signing algorithm.
5. Record the tenant domain shown by Auth0. The hostname, without a path, becomes `AUTH0_DOMAIN`.

Do not choose HS256. The server accepts only RS256 access tokens and retrieves the public signing keys from the configured tenant JWKS endpoint.

### 2. Add API permissions

On the API **Permissions** tab, create these permissions exactly:

| Permission | Intended use |
|---|---|
| `read:backlogs` | Read canonical backlog data and export YAML |
| `write:backlogs` | Create, update, move, and delete targeted backlog items |
| `operate:backlogs` | Reconcile PostgreSQL state to the provider projection |
| `admin:backlogs` | Import a canonical snapshot or purge a provider projection |

On the API **Settings** tab, enable **RBAC**. The server authorizes from the standard space-delimited `scope` claim. **Add Permissions in the Access Token** may remain disabled; Johnny-Johnny intentionally does not treat the optional `permissions` claim as a substitute for requested/granted scopes.

### 3. Define cumulative roles for human clients

Human-facing web and mobile clients will request scopes through an interactive OAuth/OIDC flow. In the Auth0 dashboard:

1. Open **User Management → Roles** and create the role.
2. Open the role's **Permissions** tab, choose **Add Permissions**, select the Johnny-Johnny API, and add the permissions shown below.
3. Assign the role from **User Management → Users → USER → Roles**.
4. When configuring the future web or native client, request the API audience and only the scopes needed by the current action.

Use cumulative roles:

| Suggested role | Permissions |
|---|---|
| Reader | `read:backlogs` |
| Editor | `read:backlogs`, `write:backlogs` |
| Operator | Reader + Editor + `operate:backlogs` |
| Administrator | all four permissions |

The API does not authorize from role names. Roles are an Auth0 management convenience that grants API permissions, while the API enforces the resulting `scope` values. `admin:backlogs` is not a wildcard; an administrator role must include every permission it needs.

### 4. Create a local M2M smoke-test application

For command-line testing:

1. Open **Applications → Applications** and choose **Create Application**.
2. Name it `Johnny-Johnny Local Smoke Test`.
3. Select **Machine to Machine Applications**.
4. Select the Johnny-Johnny API.
5. Initially authorize only `read:backlogs`. Add broader permissions only when intentionally exercising mutations or operational endpoints.
6. Record the application client ID and client secret. Keep the secret out of Git, shell history, the API `.env`, container images, and Kubernetes manifests.

The client grant is the maximum permission set the M2M application can receive. A fresh access token is required after changing its grant.

## Start the Secured REST API

Local development can remain loopback-only:

```bash
uv run jj serve --host 127.0.0.1 --port 8000
```

The server fails closed at startup if `AUTH0_DOMAIN` or `AUTH0_AUDIENCE` is missing. In a container or EKS pod, bind the process to the pod network interface:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

`0.0.0.0` provides reachability, not security. The EKS phase adds TLS ingress, secret delivery, network controls, rollout verification, and a build/deploy loop around this application boundary.

API resources:

```text
Swagger UI:  http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
OpenAPI:     http://127.0.0.1:8000/openapi.json
Base path:   http://127.0.0.1:8000/api/v1
```

Set `JOHNNY_JOHNNY_API_DOCS_ENABLED=false` to remove Swagger UI, ReDoc, and OpenAPI from a deployment. Liveness and readiness remain public and return only minimal status.

## Obtain a Token and Exercise Authentication

Set values from the M2M application and the Auth0 API. Enter the secret at the prompt so it is not saved in the command itself:

```bash
export AUTH0_DOMAIN='your-tenant.us.auth0.com'
export AUTH0_AUDIENCE='https://api.johnny-johnny.local'
export AUTH0_CLIENT_ID='your-m2m-client-id'

# Prevent shell tracing from exposing the secret or token request.
set +x
read -rsp 'Auth0 M2M client secret: ' AUTH0_CLIENT_SECRET
echo
export AUTH0_CLIENT_SECRET

TOKEN_REQUEST="$(
  python3 - <<'PY'
import json
import os

print(json.dumps({
    "client_id": os.environ["AUTH0_CLIENT_ID"],
    "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
    "audience": os.environ["AUTH0_AUDIENCE"],
    "grant_type": "client_credentials",
}))
PY
)"

TOKEN_RESPONSE="$(
  printf '%s' "${TOKEN_REQUEST}" \
    | curl -fsS -X POST \
        "https://${AUTH0_DOMAIN}/oauth/token" \
        -H 'Content-Type: application/json' \
        --data-binary @-
)"

export ACCESS_TOKEN="$(
  printf '%s' "${TOKEN_RESPONSE}" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])'
)"

unset AUTH0_CLIENT_SECRET TOKEN_REQUEST TOKEN_RESPONSE
```

First prove the boundary rejects an unauthenticated request:

```bash
curl -i 'http://127.0.0.1:8000/api/v1/auth/whoami'
```

Expected status and error code:

```text
HTTP/1.1 401 Unauthorized
authentication_required
```

Then validate the real Auth0 token without touching PostgreSQL:

```bash
curl -fsS \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  'http://127.0.0.1:8000/api/v1/auth/whoami' \
  | python3 -m json.tool
```

Example shape:

```json
{
  "subject": "CLIENT_ID@clients",
  "client_id": "CLIENT_ID",
  "scopes": [
    "read:backlogs"
  ]
}
```

Finally exercise a PostgreSQL-backed read after setting the existing project values:

```bash
export PROJECT_PATH='Johnny-Johnny%20Backlog%20Persistence%20Sandbox'
export PROVIDER_ACCOUNT='ggortsema'

curl -fsS \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "http://127.0.0.1:8000/api/v1/backlogs/${PROJECT_PATH}/summary?provider=github&provider_account=${PROVIDER_ACCOUNT}" \
  | python3 -m json.tool
```

A valid token with the wrong audience, issuer, signature, algorithm, expiry, or permission is rejected before a backlog workflow runs. Use the OAuth `access_token` issued for the Johnny-Johnny API audience; do not send an ID token or an Auth0 Management API token to this API.

## Auth0 Troubleshooting

| Result | Most likely cause | Check |
|---|---|---|
| Startup fails with `AUTH0_DOMAIN is required` or `AUTH0_AUDIENCE is required` | Server configuration is incomplete | Copy `.env.example`, use the tenant/custom-domain hostname only, and use the API's exact Identifier as the audience |
| `401 authentication_required` | No bearer token reached the API | Confirm the header is exactly `Authorization: Bearer TOKEN` |
| `401 invalid_access_token` | Wrong issuer/audience, expired token, wrong signing key/algorithm, malformed token, or ID token used by mistake | Obtain a fresh access token from the same configured domain and audience |
| `403 insufficient_scope` | The token is valid but its `scope` omits the route permission | Grant the M2M client or human role the permission, request it in the client flow when applicable, and obtain a fresh token |
| `503 authentication_service_unavailable` | The API could not retrieve a needed Auth0 signing key | Verify DNS/HTTPS egress to the configured Auth0 domain and retry after connectivity is restored |
| `whoami` works but a backlog call fails with `503 persistence_unavailable` | Auth0 is correct; PostgreSQL is not ready | Check `DATABASE_URL` and `/api/v1/health/ready` |

Do not paste bearer tokens or client secrets into online JWT decoders, tickets, logs, chat, or screenshots. Use `/api/v1/auth/whoami` to confirm the validated identity and scopes without exposing raw claims.

## Authorization Policy

| Surface | Authentication | Required permission |
|---|---|---|
| `/api/v1/health/live` | Public | none |
| `/api/v1/health/ready` | Public | none; response is deliberately minimal |
| `/api/v1/auth/whoami` | Valid Auth0 access token | none |
| Backlog summary, lists, detail, export | Valid access token | `read:backlogs` |
| Create, update, move, delete issue | Valid access token | `write:backlogs` |
| Reconciliation | Valid access token | `operate:backlogs` |
| YAML import and provider purge | Valid access token | `admin:backlogs` |

Missing or invalid authentication returns `401`. A valid token without the route permission returns `403` with the required scope in the error details and `WWW-Authenticate` challenge.

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

See `docs/api/backlog-rest-api.md` for the complete security, endpoint, and error contract.

# Complete Curl Walkthrough

The following sequence exercises the protected backlog surface. Use a disposable or explicitly designated sandbox project for confirmed mutations, especially import, purge, and full reconciliation.

The token used for the complete sequence must contain all four API permissions. Grant them only to a temporary administrative smoke-test M2M application, obtain a fresh token using the earlier token command, and revoke or rotate that client after testing.

Open a second terminal after starting the server and set these values:

```bash
export API='http://127.0.0.1:8000/api/v1'
: "${ACCESS_TOKEN:?Obtain an Auth0 access token first}"
export AUTH_HEADER="Authorization: Bearer ${ACCESS_TOKEN}"
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

## 1. Health, Authentication, and OpenAPI

Process liveness:

```bash
curl -fsS "${API}/health/live" | python3 -m json.tool
```

PostgreSQL and canonical schema readiness:

```bash
curl -fsS "${API}/health/ready" | python3 -m json.tool
```

Confirm the token without touching PostgreSQL:

```bash
curl -fsS \
  -H "${AUTH_HEADER}" \
  "${API}/auth/whoami" \
  | python3 -m json.tool
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
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/summary?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List epics:

```bash
curl -fsS \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/epics?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List all issues:

```bash
curl -fsS \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/items?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

List everything except Done:

```bash
curl -fsS -G \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/items" \
  --data-urlencode 'provider=github' \
  --data-urlencode "provider_account=${PROVIDER_ACCOUNT}" \
  --data-urlencode 'exclude_status=Done' \
  | python3 -m json.tool
```

Describe one canonical item:

```bash
curl -fsS \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/items/${EXISTING_ITEM_ID}?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

## 3. Create Two Smoke-Test Epics

Preview the source epic:

```bash
curl -fsS -X POST \
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/items/rest-api-smoke-issue?${LOCATION_QUERY}" \
  | python3 -m json.tool
```

## 6. Move the Issue

Preview the move:

```bash
curl -fsS -X POST \
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/export?${LOCATION_QUERY}" \
  -o /tmp/johnny-johnny-backlog.yml

head -40 /tmp/johnny-johnny-backlog.yml
```

Preview importing that same snapshot. The dry run parses and summarizes YAML without connecting to PostgreSQL:

```bash
curl -fsS -X POST \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/import?mode=dry-run&provider_account=${PROVIDER_ACCOUNT}&verify=true" \
  -H 'Content-Type: application/yaml' \
  --data-binary @/tmp/johnny-johnny-backlog.yml \
  | python3 -m json.tool
```

Confirm the verified transactional snapshot replacement:

```bash
curl -fsS -X POST \
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue?mode=dry-run&${LOCATION_QUERY}" \
  | python3 -m json.tool
```

Confirm deletion from PostgreSQL and the targeted GitHub projection:

```bash
curl -fsS -X DELETE \
  -H "${AUTH_HEADER}" \
  "${API}/backlogs/${PROJECT_PATH}/issues/rest-api-smoke-issue?mode=confirmed&${LOCATION_QUERY}" \
  | python3 -m json.tool
```

The API currently deletes issues, not epics. The two smoke-test epics remain as canonical records unless removed through a future epic-deletion workflow or a controlled snapshot import.

## 10. Purge and Recreate the Entire Sandbox Projection

**These commands delete every Johnny-Johnny-managed GitHub issue in the selected provider projection. Canonical PostgreSQL data is retained. Run them only against a disposable or explicitly approved sandbox.**

Preview the next bounded purge chunk:

```bash
curl -fsS -X POST \
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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
  -H "${AUTH_HEADER}" \
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

The current implementation includes endpoint behavior coverage for every REST v1 path, Auth0 JWT validation, scope authorization, CLI parity, PostgreSQL persistence, targeted synchronization, reconciliation, and purge. The current applied-project result is `109 passed, 1 skipped`.

## Documentation

Start with:

- `docs/api/backlog-rest-api.md`
- `docs/architecture/adrs/ADR-005-auth0-access-token-and-permission-policy.md`
- `docs/deployment/eks-fast-testing-loop.md`
- `docs/development/security-implementation-summary-2026-07-10.md`
- `docs/development/rest-api-implementation-summary-2026-07-10.md`
- `docs/architecture/canonical-backlog-runtime-architecture.md`
- `docs/architecture/adrs/ADR-001-postgresql-canonical-backlog-runtime.md`
- `docs/architecture/adrs/ADR-002-targeted-provider-synchronization.md`
- `docs/architecture/adrs/ADR-003-rest-api-is-a-peer-adapter.md`
- `docs/database/postgres/README.md`
- `docs/specifications/backlog-v1.md`
- `docs/development/ENGINEERING_PRINCIPLES.md`
- `docs/development/WORKING_AGREEMENT.md`
