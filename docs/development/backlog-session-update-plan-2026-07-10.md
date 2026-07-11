# Backlog Session Update Plan — July 10, 2026

The canonical backlog lives in PostgreSQL. This file records canonical updates that should be applied through Johnny-Johnny rather than by editing portable YAML.

## Story State

```text
design-canonical-backlog-persistence                    Done
expose-backlog-workflows-through-rest-api               Done
secure-backlog-rest-api                                 Implemented; mark Done
deploy-johnny-johnny-api-to-eks                         Next
synchronize-github-project-events-to-canonical-backlog Following
```

The project sequence remains:

```text
canonical persistence
  -> REST adapter
  -> Auth0 authentication and API authorization
  -> EKS deployment over HTTPS
  -> signed GitHub webhook synchronization
```

## Confirm the REST Story

Story:

```text
ID: expose-backlog-workflows-through-rest-api
Title: Expose Backlog Workflows Through REST API
```

The REST adapter remains implemented. Its historical completion evidence is preserved in:

```text
docs/development/rest-api-implementation-summary-2026-07-10.md
```

Confirm its canonical status before applying later story updates:

```bash
uv run jj backlog describe \
  expose-backlog-workflows-through-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox"
```

If it is not Done, use the historical completion command in the REST implementation summary or adapt the following command to the current engineering backlog project:

```bash
uv run jj backlog update \
  expose-backlog-workflows-through-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --status "Done" \
  --comment "Implemented the versioned FastAPI backlog surface with typed contracts, explicit dry-run/confirmed semantics, shared PostgreSQL-backed workflows, stable errors, YAML import/export boundaries, OpenAPI documentation, and endpoint behavior coverage." \
  --confirm
```

## Complete the Auth0 Security Story

Story:

```text
ID: secure-backlog-rest-api
Title: Secure Backlog REST API
Suggested capability: Platform Security
```

Implemented behavior:

- Auth0 selected and recorded as the initial OAuth 2.0/OpenID Connect provider
- server-owned issuer and audience configuration
- fixed `RS256` validation through the configured Auth0 JWKS
- signature, issuer, audience, expiry, issued-at, optional not-before, subject, and signing-key validation
- rejection of token-controlled remote key locations and unsupported critical headers
- stable `401`, `403`, and authentication-service `503` responses
- scope-based API authorization independent of web or mobile clients
- permissions for read, targeted write, reconciliation, and administrative operations
- identical authorization requirements for dry-run and confirmed requests
- public, minimal liveness and readiness probes
- protected `/api/v1/auth/whoami` token smoke endpoint that does not use PostgreSQL
- fail-closed application startup with no production authentication-bypass switch
- optional removal of Swagger UI, ReDoc, and OpenAPI in deployed environments
- complete Auth0 tenant and M2M setup instructions in the root README
- behavior coverage for token validation and every route policy
- applied-project result: `109 passed, 1 skipped`

Primary evidence:

```text
README.md
docs/api/backlog-rest-api.md
docs/architecture/adrs/ADR-005-auth0-access-token-and-permission-policy.md
docs/development/security-implementation-summary-2026-07-10.md
tests/behavior/test_auth0_access_token_validation.py
tests/behavior/test_backlog_rest_api.py
```

Suggested canonical completion update:

```bash
uv run jj backlog update \
  secure-backlog-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --status "Done" \
  --comment "Implemented Auth0 RS256/JWKS access-token validation and scope-based authorization for the FastAPI backlog surface. Added read:backlogs, write:backlogs, operate:backlogs, and admin:backlogs route policy; minimal public health probes; protected token-only whoami smoke endpoint; stable 401/403/503 behavior; fail-closed startup; Auth0 setup and curl documentation; and behavior coverage for validation and authorization. Final local suite: 109 passed, 1 skipped." \
  --confirm
```

Use the correct canonical project title if the engineering backlog is bound to a different provider project.

## Next Story — Deploy the Secured API to EKS

Story:

```text
ID: deploy-johnny-johnny-api-to-eks
```

Description:

```text
Package and deploy the Auth0-secured Johnny-Johnny API to EKS behind HTTPS with reproducible container publication, Kubernetes health probes, server-owned secret delivery, controlled network exposure, rollout verification, and an authenticated fast-testing loop.
```

The implementation contract is recorded in:

```text
docs/deployment/eks-fast-testing-loop.md
```

Acceptance criteria should include:

1. A reproducible container image starts the API with `jj serve --host 0.0.0.0 --port 8000`.
2. The image is tagged immutably and published to an approved ECR repository.
3. A Kubernetes Deployment and ClusterIP Service expose port 8000 only inside the cluster boundary.
4. Liveness and readiness probes use the public minimal `/api/v1/health/live` and `/api/v1/health/ready` endpoints.
5. External API traffic is exposed only through HTTPS ingress.
6. Backlog routes remain protected by Auth0 after deployment; ingress identity controls do not replace application authorization.
7. `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` are supplied as deployment configuration.
8. `DATABASE_URL` and `GITHUB_TOKEN` are delivered through the selected secret mechanism and are never committed to source control, image layers, or rendered manifests.
9. PostgreSQL remains privately reachable and is not exposed as part of the deployment.
10. Pod identity, security context, resource requests/limits, and network controls are explicit.
11. Rollout status, failure diagnostics, rollback, and authenticated smoke tests are reproducible.
12. A Bash fast loop builds, pushes, deploys, waits for rollout, verifies public probes, obtains or consumes a smoke-test token safely, and calls `/api/v1/auth/whoami` plus one read-scoped endpoint.
13. Request and principal correlation can be observed without logging bearer tokens, client secrets, or raw token claims.

Concrete inputs to resolve before writing the deployment artifacts:

- AWS account ID and region
- EKS cluster name and namespace
- ECR repository name
- ingress controller and DNS hostname
- TLS certificate strategy
- Kubernetes secret delivery mechanism
- PostgreSQL network path
- service account and IAM role strategy
- Auth0 smoke-test client ownership and token handling

The owning epic should be selected by the capability improved, not merely by repository or Kubernetes implementation location.

## Following Story — Synchronize GitHub Events into PostgreSQL

Story:

```text
ID: synchronize-github-project-events-to-canonical-backlog
Suggested capability: Backlog as Code Synchronization
```

Description:

```text
Receive authenticated GitHub webhook deliveries and synchronize authoritative GitHub Project and issue changes into canonical PostgreSQL state without treating webhook payloads as trusted canonical state.
```

Acceptance criteria should include:

- a narrowly scoped HTTPS webhook endpoint accepts GitHub deliveries
- the raw request body is verified against `X-Hub-Signature-256` using a server-owned secret
- missing or invalid signatures are rejected before event processing
- `X-GitHub-Delivery` is persisted or otherwise used for idempotent duplicate detection
- supported event types are explicit and unsupported events are acknowledged safely
- the webhook acts as a trigger to fetch authoritative current GitHub state where necessary
- provider changes are mapped through provider adapters into canonical application workflows
- partial failure, retry, ordering, and replay behavior are explicit
- behavior tests cover valid signatures, invalid signatures, duplicates, unsupported events, and canonical updates
- webhook authentication remains separate from Auth0 bearer-token authentication

## Deferred Work Retained

- live REST reconciliation against the disposable sandbox, when intentionally desired
- live REST purge only when intentionally proving destruction and reconstruction
- durable operation runs and retry/backoff state
- provider throttling and rate-limit handling
- explicit provider-project rebinding
- replacement of the legacy `generate` flow
- PostgreSQL private-network migration and rotation/removal of temporary public development exposure
