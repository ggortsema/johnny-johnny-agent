# Session Index

**Date:** July 10, 2026  
**Project:** Johnny-Johnny Agent  
**Project Version:** 0.1.0  
**Git Branch:** dev  
**Completed Story:** `secure-backlog-rest-api`  
**Next Story:** `deploy-johnny-johnny-api-to-eks`  
**Following Story:** `synchronize-github-project-events-to-canonical-backlog`

## Session Summary

This session secured the existing FastAPI backlog adapter with Auth0 access-token validation and API-side authorization.

The implementation now validates Auth0 `RS256` access tokens against a trusted, server-configured issuer/JWKS and enforces one of four OAuth permissions before a backlog workflow is dispatched:

```text
read:backlogs
write:backlogs
operate:backlogs
admin:backlogs
```

Liveness and readiness remain unauthenticated for Kubernetes and load-balancer probes but return only minimal operational state. A protected `/api/v1/auth/whoami` endpoint provides a real-token smoke test without connecting to PostgreSQL or GitHub.

The applied-project behavior suite completed with:

```text
109 passed, 1 skipped
```

The generated OpenAPI surface contains:

```text
14 paths / 16 HTTP operations
```

The skipped test requires live GitHub provider access. The Auth0 validation and route-authorization tests are self-contained and make no Auth0 network calls.

## Completed Story

### `secure-backlog-rest-api`

Implemented behavior includes:

- Auth0 selected as the initial OAuth 2.0/OpenID Connect provider
- required server-owned `AUTH0_DOMAIN` and `AUTH0_AUDIENCE`
- application startup that fails closed when security configuration is missing
- fixed `RS256` token validation through the configured tenant JWKS
- signature, issuer, audience, expiration, issued-at, optional not-before, subject, and key-ID validation
- rejection of token-selected `jku`/`x5u` key sources and unsupported critical headers
- support for Auth0 default and RFC 9068 client metadata claims
- authorization from the standard space-delimited `scope` claim
- no privilege escalation from the optional Auth0 `permissions` claim
- stable `401 Unauthorized`, `403 Forbidden`, and authentication-service `503 Service Unavailable` errors
- route-level read, write, operate, and admin permission policy
- identical permission checks for dry-run and confirmed operations
- public minimal `/api/v1/health/live` and `/api/v1/health/ready`
- protected token-only `/api/v1/auth/whoami`
- optional removal of Swagger UI, ReDoc, and OpenAPI in deployments
- an application factory with an injectable verifier for behavior tests and no production authentication-bypass switch
- complete Auth0 API, permission, RBAC, role, M2M, token, and curl instructions in the root README

The canonical completion command and comment are recorded in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Authorization Policy

| Surface | Authentication | Required permission |
|---|---|---|
| Liveness | Public | none |
| Readiness | Public, minimal response | none |
| `/api/v1/auth/whoami` | Valid Auth0 access token | none |
| Summary, list, detail, export | Valid access token | `read:backlogs` |
| Create, update, move, delete | Valid access token | `write:backlogs` |
| Reconciliation | Valid access token | `operate:backlogs` |
| YAML import and provider purge | Valid access token | `admin:backlogs` |

`admin:backlogs` is not a wildcard. Human Auth0 roles should be cumulative, and M2M client grants should remain least privilege.

## Auth0 Tenant Work Remaining

The code and documentation are ready. Tenant-side configuration still needs to be completed in the user's Auth0 account:

1. Create the Johnny-Johnny API with a stable identifier and `RS256` signing.
2. Add the four exact permissions.
3. Enable RBAC for the API.
4. Create a least-privilege Machine-to-Machine smoke application.
5. Put the tenant domain and API identifier into the local `.env` as `AUTH0_DOMAIN` and `AUTH0_AUDIENCE`.
6. Obtain a client-credentials access token and exercise `/api/v1/auth/whoami` using the README command.
7. Add broader smoke permissions only when intentionally testing mutations, reconciliation, import, or purge.

Auth0 client credentials belong to the caller and are deliberately not part of the API `.env.example`.

## Architectural Decisions

1. Auth0 is the initial identity provider, while the API remains a standards-based OAuth resource server.
2. Auth0 configuration is confined to the HTTP security boundary; the canonical domain and application workflows remain provider independent.
3. The API authorizes from `scope`, not role names and not the optional `permissions` claim.
4. The accepted signing algorithm and JWKS location are server controlled.
5. Every backlog operation is protected independently of browser, mobile, ingress, or network controls.
6. Health probes remain public because Kubernetes and load balancers need them, but they expose no connection strings, exception text, table names, migration details, or credentials.
7. Dry-run is a mutation preview, not an authorization bypass.
8. GitHub webhook authentication remains a separate future HMAC-SHA256 trust boundary.
9. Binding to `0.0.0.0` inside a pod provides reachability only; Auth0 authorization and HTTPS ingress remain required.
10. The next deployment loop must not put database credentials, GitHub tokens, Auth0 client secrets, or bearer tokens in source control, image layers, manifests, command-line arguments, or shell traces.

See:

```text
docs/architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md
docs/architecture/adrs/ADR-005-auth0-access-token-and-permission-policy.md
docs/architecture/api-security-deployment-and-client-evolution.md
```

## Production Files Added

```text
.env.example
src/johnny_johnny_agent/api/security.py
tests/behavior/test_auth0_access_token_validation.py
```

## Production Files Updated

```text
.gitignore
pyproject.toml
uv.lock
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/api/app.py
src/johnny_johnny_agent/api/errors.py
src/johnny_johnny_agent/api/models.py
src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/api/serialization.py
src/johnny_johnny_agent/cli/main.py
tests/behavior/test_backlog_rest_api.py
```

## Documentation Added

```text
docs/architecture/adrs/ADR-005-auth0-access-token-and-permission-policy.md
docs/deployment/README.md
docs/deployment/eks-fast-testing-loop.md
docs/development/security-implementation-summary-2026-07-10.md
```

## Documentation Updated

```text
README.md
docs/api/backlog-rest-api.md
docs/architecture/adrs/ADR-003-rest-api-is-a-peer-adapter.md
docs/architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md
docs/architecture/api-security-deployment-and-client-evolution.md
docs/architecture/canonical-backlog-runtime-architecture.md
docs/development/DECISION_LOG.md
docs/development/README.md
docs/development/backlog-persistence-test-strategy.md
docs/development/backlog-session-update-plan-2026-07-10.md
docs/development/commands-left-off.txt
docs/development/rest-api-implementation-summary-2026-07-10.md
docs/development/session-index.md
session-index.md
```

## Verification

```text
Python behavior suite: 109 passed, 1 skipped
OpenAPI surface: 14 paths / 16 operations
Bearer security scheme: generated
Public probes: no OpenAPI bearer requirement
Protected routes: Auth0 bearer requirement generated
Auth0 validation: self-contained RSA/JWT tests passed
Route authorization: read/write/operate/admin positive and independent-denial behavior passed
Interactive docs removal: behavior-tested
README token and endpoint exercises: documented
```

No live Auth0 tenant call was made because the tenant was being created during this session. No live REST purge or reconciliation was executed because those remain broad or destructive provider operations.

## Next Story

### `deploy-johnny-johnny-api-to-eks`

The deployment contract is ready in:

```text
docs/deployment/eks-fast-testing-loop.md
```

The next phase should add:

- container build definition and ignore rules
- immutable ECR image publication
- Kubernetes namespace/configuration/secret integration
- Deployment, ClusterIP Service, probes, resources, and security context
- HTTPS ingress and DNS/certificate wiring
- private PostgreSQL connectivity
- controlled Auth0/GitHub egress
- rollout and rollback behavior
- a Bash build/push/deploy/wait/authenticated-smoke loop

The EKS story needs the concrete AWS account, region, cluster, namespace, repository, DNS, ingress, certificate, secret-management, PostgreSQL-network, and IAM choices before deployment artifacts can be finalized.

## Following Story

### `synchronize-github-project-events-to-canonical-backlog`

After the secured EKS endpoint exists, add the public GitHub webhook route, raw-body HMAC-SHA256 verification, delivery idempotency, provider-state refresh, and provider-to-canonical synchronization. This endpoint must not reuse or weaken the Auth0 bearer boundary.

## Category Review

- **ADRs:** Updated; ADR-005 records the concrete Auth0 decision and ADR-004 retains the separate webhook boundary.
- **Architecture documentation:** Updated for the implemented security path and next EKS boundary.
- **API contract:** Updated with token validation, scopes, public probes, errors, and the `whoami` smoke endpoint.
- **Deployment documentation:** Added an EKS fast-loop implementation contract; no Kubernetes resources or deploy script are falsely claimed complete.
- **Specifications:** Reviewed; no canonical backlog or YAML specification change was required.
- **Database documentation:** Reviewed; no schema or persistence decision changed.
- **Engineering Principles:** Reviewed; the existing domain-first, provider-adapter, explicit-boundary, behavior-first, and durable-knowledge principles already cover this phase.
- **Working Agreement:** Reviewed; no process change was required.
- **AI Collaboration documentation:** Reviewed; no collaboration-process change was required.
- **Behavior tests:** Expanded and passing.
- **Backlog:** Durable completion command recorded; canonical mutation remains to be applied through `jj` if not already done.

## Immediate First Task

Complete the Auth0 dashboard setup in `README.md`, start the API, obtain a least-privilege M2M token, and exercise:

```bash
curl -fsS \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  http://127.0.0.1:8000/api/v1/auth/whoami \
  | python3 -m json.tool
```

Then confirm `secure-backlog-rest-api` is Done in the canonical backlog and begin the EKS story from `docs/deployment/eks-fast-testing-loop.md`.
