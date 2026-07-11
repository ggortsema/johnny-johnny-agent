# Canonical Backlog Runtime Architecture

**Status:** Implemented secured baseline  
**Date:** July 10, 2026

## Purpose

Describe the runtime architecture after migrating backlog commands to PostgreSQL canonical persistence, exposing shared workflows through REST, and securing the HTTP boundary with Auth0.

## Runtime Shape

```text
CLI ───────────────────────┐
Auth0-secured REST API ────┼── application workflows ── canonical domain
signed webhooks later ─────┘            │
                                        ├── PostgreSQL repository
                                        └── provider adapters (GitHub first)
```

Presentation adapters reuse application workflows. The REST server imports those workflows directly and never shells out to CLI commands. Authentication is an HTTP adapter concern and does not enter the canonical domain.

## Secured REST Adapter Path

```text
HTTP request
  -> bearer extraction
  -> Auth0 RS256/JWKS, issuer, audience, and time validation
  -> route-scope authorization
  -> typed FastAPI request model
  -> explicit dry-run or confirmed mode
  -> shared PostgreSQL-backed application workflow
  -> typed response model or consistent HTTP error
```

Implemented REST behavior:

- token-only identity exercise at `/api/v1/auth/whoami`
- public minimal liveness and readiness
- read parity for inspect, list epics, list items, describe, and export
- targeted mutation parity for create epic, create issue, update, move, and delete issue
- operational parity for reconcile, purge, and YAML import
- one explicit `mode` contract for previews and confirmed mutations
- server-owned database and identity-provider configuration
- direct YAML request/response handling only at the portable import/export boundary

See `docs/api/backlog-rest-api.md`, ADR-003, ADR-004, and ADR-005.

## Authentication and Authorization Boundary

Auth0 is the initial OAuth 2.0/OpenID Connect provider. The API is an OAuth resource server and requires audience-specific bearer access tokens.

```text
read:backlogs     summary, list, detail, export
write:backlogs    create, update, move, delete issue
operate:backlogs  reconcile
admin:backlogs    import, purge
```

The API authorizes from `scope`. Auth0 role names and the optional `permissions` claim are not application policy inputs.

Dry-run and confirmed forms use the same permission. A preview does not bypass authorization.

The production application has no runtime “disable auth” switch. Tests inject an `AccessTokenVerifier` into the FastAPI application factory.

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

REST invokes the same workflows only after access-token and route-scope checks. See ADR-002 for failure and compensation behavior.

## Full Projection Workflows

### Reconcile

`jj backlog reconcile` and the `operate:backlogs` REST endpoint compare PostgreSQL canonical state with the bound GitHub Project and execute a provider plan.

- Default bounded scope: 100 provider operations.
- `--max-operations N`: soft budget; complete item groups are not intentionally split.
- `--all`: execute the complete currently planned scope.
- A rerun reads live state, rebuilds the plan, and skips completed work.

An operation means a provider action, not an issue. One item may require create, add-to-project, status, parent, and comment operations. Acceptance criteria are rendered inside the issue body.

### Purge

`jj maintenance purge` and the `admin:backlogs` REST endpoint delete Johnny-Johnny-managed GitHub issues while preserving canonical PostgreSQL state.

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

REST YAML import requires `admin:backlogs`. REST YAML export requires `read:backlogs`.

`jj backlog generate` remains temporarily as a GitHub-to-YAML migration utility. It is deferred for replacement by a renamed GitHub-to-PostgreSQL import workflow after durable provider execution is implemented.

`jj backlog pull` remains a raw GitHub diagnostic.

Removed legacy commands:

```text
jj backlog publish
jj backlog preview-epic-body
```

## Provider Project Binding

The command option `--project` and REST path identify the stored `provider_projects` row. The row's external ID determines the GitHub Project target.

Runtime reconciliation does not search GitHub by title and silently rewrite the binding. Rebinding must be an explicit future capability.

## Probe and Deployment Boundary

Public operational routes:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
```

They expose only minimal categories needed by Kubernetes and a load balancer. `/api/v1/auth/whoami` is protected and validates token identity without database access.

Local development normally binds to `127.0.0.1`. An EKS pod binds to `0.0.0.0`; Kubernetes Service, HTTPS ingress, network policy, secret delivery, and application authorization together control exposure.

Auth0 issuer and audience are server configuration. Database and GitHub credentials are server secrets. Auth0 M2M client secrets belong to callers and must not be deployed with the API.

## Separate Webhook Boundary

Future GitHub webhook deliveries use HMAC-SHA256 verification over the raw request body and deduplication by `X-GitHub-Delivery`. They do not use Auth0 access tokens.

Inbound webhook verification credentials and outbound GitHub provider credentials remain separate.

## Next Evolution

The agreed order is now:

1. ~~secure the REST API~~ completed with Auth0 and scope authorization
2. deploy the secured service to EKS over HTTPS
3. add signed GitHub webhook ingestion and provider-to-canonical synchronization

Later evolutions add:

- durable reconcile runs and operations
- rate-aware workers and asynchronous operation resources where needed
- audit history and authenticated-subject attribution
- explicit provider-project rebinding
- project/resource-level authorization if needed
- responsive web and native mobile clients over the same authenticated backend
