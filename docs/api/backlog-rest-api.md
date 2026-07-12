# Johnny-Johnny REST API

**Status:** Implemented locally, Auth0-secured v1; assistant deployment acceptance pending
**Base path:** `/api/v1`
**Server command:** `uv run jj serve`

## Purpose

The REST API is a peer presentation adapter to the Johnny-Johnny CLI. It calls the same PostgreSQL-backed application workflows directly and never shells out to `jj`.

```text
CLI ───────────────────────┐
Auth0-secured REST API ────┼── application workflows ── canonical domain
                           │            │
                           │            ├── PostgreSQL canonical store
                           │            ├── GitHub provider adapter
                           │            └── language-model provider adapter
                           └── typed request/response contracts
```

PostgreSQL remains canonical runtime state. GitHub remains a provider projection. YAML appears only at the explicit import/export boundary.

## Security Boundary

### Authentication

Protected requests carry an Auth0 access token issued for the Johnny-Johnny API audience. An ID token or Auth0 Management API token is not accepted:

```http
Authorization: Bearer ACCESS_TOKEN
```

The API validates the token as an RS256 JWT using the public key selected from the configured Auth0 JWKS endpoint. Validation requires:

- a token signing algorithm of exactly `RS256`
- a signing-key ID in `kid`
- a signature valid for the selected issuer key
- an `iss` claim equal to `https://AUTH0_DOMAIN/`
- an `aud` claim containing the configured `AUTH0_AUDIENCE`
- valid `exp`, `iat`, and optional `nbf` times
- a non-empty `sub` claim

The JWKS URL is constructed only from server-owned `AUTH0_DOMAIN`. Token headers cannot redirect key retrieval: `jku`, `x5u`, and unsupported critical headers are rejected.

The verifier accepts both Auth0's default access-token profile and the RFC 9068 profile. It reads a calling application ID from `azp` or `client_id`, but authorization is based only on granted OAuth scopes.

### Authorization

Johnny-Johnny enforces the space-delimited `scope` claim. The optional Auth0 `permissions` claim is not accepted as a substitute for requested and granted scopes.

| Surface | Required permission |
|---|---|
| `/api/v1/auth/whoami` | valid access token; no API permission required |
| Assistant response generation | `invoke:assistant` |
| Backlog summary, lists, detail, export | `read:backlogs` |
| Create epic, create issue, update, move, delete issue | `write:backlogs` |
| Reconciliation | `operate:backlogs` |
| YAML import and provider purge | `admin:backlogs` |

Permissions are independent. `admin:backlogs` is not a wildcard. Auth0 roles should be cumulative when a human operator needs multiple capabilities.

### Public probes

These routes remain unauthenticated for Kubernetes and load-balancer probes:

| Method | Path | Public response |
|---|---|---|
| `GET` | `/api/v1/health/live` | service, version, `ok` |
| `GET` | `/api/v1/health/ready` | service, version, ready/not-ready, minimal database/schema checks |

Readiness never returns database hostnames, usernames, server versions, table names, exception messages, or connection details.

### Authentication exercise

`GET /api/v1/auth/whoami` validates a real token without calling PostgreSQL or GitHub. It returns only:

```json
{
  "subject": "CLIENT_ID@clients",
  "client_id": "CLIENT_ID",
  "scopes": ["read:backlogs"]
}
```

It does not echo the raw access token or arbitrary claims.

## Auth0 Resource Setup

Create one Auth0 API with:

```text
Name: Johnny-Johnny API
Identifier / audience: https://api.johnny-johnny.local
Signing algorithm: RS256
RBAC: enabled
```

Add these API permissions exactly:

```text
read:backlogs
write:backlogs
operate:backlogs
admin:backlogs
invoke:assistant
```

The API reads `scope`, so Auth0's **Add Permissions in the Access Token** setting may remain disabled. For local curl testing, create a Machine-to-Machine application, select the Johnny-Johnny API, and grant only the permissions needed for the test.

The project README contains the complete dashboard walkthrough, token request, 401 test, `/auth/whoami` test, assistant exercise, and PostgreSQL-backed endpoint exercise.

## Runtime Configuration

The process reads the project-root `.env` file and environment variables:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
GITHUB_TOKEN=github-token-with-required-project-and-issue-permissions
OPENAI_API_KEY=server-owned-openai-key
OPENAI_MODEL=gpt-5.6
OPENAI_MODELS=gpt-5.6
JOHNNY_JOHNNY_PROVIDER_ACCOUNT=ggortsema

AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.johnny-johnny.local
JOHNNY_JOHNNY_API_DOCS_ENABLED=true

AUTH0_CLOCK_SKEW_SECONDS=30
AUTH0_JWKS_TIMEOUT_SECONDS=5
AUTH0_JWKS_CACHE_SECONDS=300
```

| Setting | Required for server | Purpose |
|---|---:|---|
| `DATABASE_URL` | for persistence workflows/readiness | Canonical PostgreSQL connection |
| `GITHUB_TOKEN` | for confirmed provider workflows | Outbound GitHub credential |
| `OPENAI_API_KEY` | yes | Server-owned OpenAI credential for assistant responses |
| `OPENAI_MODEL` | yes | Default assistant model |
| `OPENAI_MODELS` | no | Comma-separated server allow-list exposed to authenticated clients; default model is always included |
| `JOHNNY_JOHNNY_PROVIDER_ACCOUNT` | no | Default provider account |
| `AUTH0_DOMAIN` | yes | Trusted issuer hostname and JWKS origin |
| `AUTH0_AUDIENCE` | yes | Exact Auth0 API identifier |
| `JOHNNY_JOHNNY_API_DOCS_ENABLED` | no | Serve or remove Swagger UI, ReDoc, and OpenAPI; default `true` |
| `AUTH0_CLOCK_SKEW_SECONDS` | no | Non-negative JWT time leeway; default `30` |
| `AUTH0_JWKS_TIMEOUT_SECONDS` | no | Positive JWKS request timeout; default `5` |
| `AUTH0_JWKS_CACHE_SECONDS` | no | Positive JWKS set cache lifetime; default `300` |

The server fails closed when Auth0 issuer configuration or required OpenAI configuration is missing or malformed. It does not need an Auth0 client ID or client secret. Client credentials belong to the calling application and must not be deployed with the API. `OPENAI_API_KEY` is server-owned and must not be delivered to a web or native client.

HTTP clients cannot submit a database URL, GitHub token, OpenAI key, arbitrary model identifier, Auth0 domain, audience, JWKS URL, or other server security settings. An assistant request may select only a model returned by the server-owned `/assistant/models` catalog.

## Starting the Server

Local loopback:

```bash
uv sync
uv run jj serve --host 127.0.0.1 --port 8000
```

Container or EKS pod:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

Binding to `0.0.0.0` provides pod-network reachability only. EKS deployment must add HTTPS ingress, server-owned secret delivery, network controls, and rollout/smoke-test behavior.

When enabled, interactive contracts are available at:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
http://127.0.0.1:8000/openapi.json
```

Swagger UI exposes an **Authorize** control for pasting a bearer token. Paste the token value itself, without adding a second `Bearer` prefix.

## Assistant Endpoints

```http
GET /api/v1/assistant/models
POST /api/v1/assistant/responses
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

Required permission:

```text
invoke:assistant
```

Model catalog response:

```json
{
  "default_model": "gpt-5.6",
  "models": [
    {"id": "gpt-5.6", "label": "gpt-5.6", "is_default": true}
  ]
}
```

Generation request:

```json
{
  "text": "What should we work on next?",
  "model": "gpt-5.6"
}
```

`model` is optional. When omitted, the configured default is used. When supplied, it must be present in the authenticated catalog.

Response:

```json
{
  "response_id": "resp_123",
  "text": "The next priority is...",
  "model": "configured-or-returned-model",
  "usage": {
    "input_tokens": 18,
    "output_tokens": 9
  }
}
```

The route calls `GenerateAssistantResponse`, which depends on the provider-neutral `LanguageModelProvider` port. The OpenAI adapter uses the Responses API and translates provider output and failures into Johnny-Johnny contracts. Retrieval, memory, tools, prompt construction, and provider selection can be introduced behind the use case without changing this route.

See `assistant-responses.md` for the complete assistant contract and smoke-test command.

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

Authentication and authorization happen before either preview or confirmed workflow dispatch. A dry run does not bypass the route permission.

## Endpoint Inventory

### Authentication and health

| Method | Path | Access | Behavior |
|---|---|---|---|
| `GET` | `/api/v1/auth/whoami` | valid token | Confirm token identity and granted scopes without database access |
| `GET` | `/api/v1/health/live` | public | Process liveness and API version |
| `GET` | `/api/v1/health/ready` | public | Minimal PostgreSQL/schema readiness; `503` when not ready |

### Reads

All read routes require `read:backlogs`.

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/v1/backlogs/{project_title}/summary` | Project identity and aggregate counts |
| `GET` | `/api/v1/backlogs/{project_title}/epics` | Ordered epic summaries |
| `GET` | `/api/v1/backlogs/{project_title}/items` | Ordered issue summaries with optional epic and status filters |
| `GET` | `/api/v1/backlogs/{project_title}/items/{item_id}` | Full epic or issue detail |
| `GET` | `/api/v1/backlogs/{project_title}/export` | Portable canonical YAML snapshot |

`GET .../items` accepts `epic_id`, repeated `status`, or repeated `exclude_status`. `status` and `exclude_status` are mutually exclusive, matching CLI behavior.

### Targeted mutations

All targeted mutation routes require `write:backlogs`.

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/backlogs/{project_title}/epics` | Preview or create one canonical epic and targeted GitHub projection |
| `POST` | `/api/v1/backlogs/{project_title}/issues` | Preview or create one canonical issue under an epic |
| `PATCH` | `/api/v1/backlogs/{project_title}/items/{item_id}` | Preview or update title, description, status, acceptance criteria, and/or comment |
| `POST` | `/api/v1/backlogs/{project_title}/issues/{issue_id}/move` | Preview or move an issue to another epic |
| `DELETE` | `/api/v1/backlogs/{project_title}/issues/{issue_id}` | Preview or delete a canonical issue and targeted GitHub projection |

Confirmed targeted mutations report success only after required GitHub synchronization and the canonical PostgreSQL commit succeed. Shared workflows retain rollback, compensation, idempotent repair, and explicit consistency-error behavior.

### Projection operations

| Method | Path | Permission | Behavior |
|---|---|---|---|
| `POST` | `/api/v1/backlogs/{project_title}/reconciliation` | `operate:backlogs` | Preview or execute a bounded/full provider reconciliation |
| `POST` | `/api/v1/backlogs/{project_title}/purge` | `admin:backlogs` | Preview or delete a bounded/full GitHub projection while retaining canonical data |

Reconciliation scope:

```json
{"mode": "dry-run", "max_operations": 100}
```

or:

```json
{"mode": "confirmed", "all": true}
```

Purge scope:

```json
{"mode": "dry-run", "max_issues": 50}
```

or:

```json
{"mode": "confirmed", "all": true}
```

`all` is mutually exclusive with the corresponding maximum. Omitting both uses the CLI-compatible defaults: 100 provider operations for reconciliation and 50 issues for purge.

### Portable YAML boundary

| Method | Path | Permission | Behavior |
|---|---|---|---|
| `POST` | `/api/v1/backlogs/import?mode=...` | `admin:backlogs` | Parse or transactionally replace one canonical snapshot from an `application/yaml` body |
| `GET` | `/api/v1/backlogs/{project_title}/export` | `read:backlogs` | Return an `application/yaml` canonical snapshot |

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
    "code": "insufficient_scope",
    "message": "The access token does not grant the permission required for this operation.",
    "details": {
      "required_scopes": ["write:backlogs"]
    }
  }
}
```

Status mapping:

| HTTP status | Error category |
|---|---|
| `400` | Invalid cross-field request |
| `401` | Missing, malformed, expired, or otherwise invalid bearer token |
| `403` | Valid token without the required route scope |
| `404` | Canonical item, epic, issue, or stored provider project not found |
| `409` | Resource conflict, round-trip failure, or cross-boundary consistency failure |
| `422` | Request-model, backlog-document, or domain validation failure |
| `502` | GitHub operation failure or controlled assistant-provider rejection/invalid response |
| `503` | PostgreSQL unavailable/readiness incomplete, issuer signing keys unavailable, or assistant provider unavailable |
| `504` | Assistant provider request timed out |
| `500` | Unexpected internal failure without implementation details in the response |

Authentication failures include a `WWW-Authenticate` response header. `401` distinguishes missing credentials from an invalid token through stable error codes. `403` includes the route's required scopes but does not return the token's raw claims.

## Test Coverage

`tests/behavior/test_auth0_access_token_validation.py` verifies:

- valid RS256 signature, issuer, audience, expiry, subject, and scope extraction
- wrong issuer, audience, expiry, subject, signing key, and algorithm rejection
- rejection of token-controlled remote-key and critical headers
- strict string handling for the `scope` claim
- no authorization escalation from the optional `permissions` claim
- JWKS outage classification
- fail-closed Auth0 configuration and application-factory startup
- explicit removal of Swagger UI, ReDoc, and OpenAPI when docs are disabled

`tests/behavior/test_backlog_rest_api.py` verifies:

- public minimal health probes
- protected OpenAPI operations and bearer security scheme
- token-only `/auth/whoami`
- `401`, `403`, and authentication-service `503` behavior before workflow dispatch
- read/write/operate/admin/invoke route policy, including independent-scope denials and proof that admin is not a wildcard
- assistant `401`, `403`, `422`, success, and controlled `502`/`503`/`504` behavior
- proof that assistant provider details are not leaked through public errors
- every v1 backlog endpoint and shared workflow dispatch
- typed operation serialization, YAML import/export, and stable application errors


`tests/unit/test_assistant_response.py`, `tests/unit/test_openai_language_model.py`, and `tests/unit/test_openai_configuration.py` verify:

- the stable use-case boundary with a fake provider;
- request trimming and blank-input rejection;
- OpenAI Responses API request shaping and normalized output;
- malformed provider response rejection;
- SDK authentication, timeout, connection, rate-limit, and status error translation;
- fail-closed OpenAI key and model configuration.

Current applied-project result:

```text
137 passed, 1 skipped
```

The skipped test requires live GitHub provider access.

## Curl Walkthrough

The project README contains:

1. exact Auth0 dashboard setup
2. a client-credentials token command
3. an unauthenticated `401` exercise
4. a successful `/api/v1/auth/whoami` exercise
5. a PostgreSQL-backed summary request
6. a sequential sandbox walkthrough for the complete protected backlog surface
