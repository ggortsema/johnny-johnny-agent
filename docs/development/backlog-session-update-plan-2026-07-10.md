# Backlog Session Update Plan — July 10, 2026

The canonical backlog lives in PostgreSQL. This file records canonical updates that should be applied through Johnny-Johnny rather than by editing YAML.

## Completed Persistence Story

The final full sandbox reconciliation completed successfully. A subsequent full dry run reported no remaining work, and the expected projection is present in GitHub.

`design-canonical-backlog-persistence` remains Done.

## Complete the REST Story

Story:

```text
ID: expose-backlog-workflows-through-rest-api
Title: Expose Backlog Workflows Through REST API
```

Completion evidence:

- versioned FastAPI surface under `/api/v1`
- PostgreSQL-backed read, mutation, reconciliation, purge, import, and export endpoints
- direct application-workflow reuse with no CLI shell invocation
- typed request/response and consistent error contracts
- explicit `dry-run` and `confirmed` mutation modes
- generated OpenAPI, Swagger UI, and ReDoc
- complete README curl walkthrough
- applied-project test result: `87 passed`
- most live curl examples exercised successfully
- live REST purge and reconciliation intentionally deferred because they are broad/destructive provider operations

Suggested canonical completion update:

```bash
uv run jj backlog update \
  expose-backlog-workflows-through-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --status "Done" \
  --comment "Implemented and live-smoke-tested the versioned FastAPI backlog surface with typed models, explicit dry-run/confirmed semantics, shared PostgreSQL-backed workflows, consistent errors, YAML import/export boundaries, OpenAPI documentation, and README curl examples. Final local suite: 87 passed. REST purge and reconcile remain intentionally unexecuted live because they are broad/destructive operations." \
  --confirm
```

Use the correct canonical project title if the engineering backlog is bound to a different provider project.

## Next Story — Secure the Existing REST API

Recommended ID:

```text
secure-backlog-rest-api
```

Recommended capability/epic:

```text
Platform Security
```

Description:

```text
Secure the existing Johnny-Johnny FastAPI surface with OAuth 2.0/OpenID Connect authentication and API-side authorization so the service can be deployed beyond loopback without making the UI the security perimeter.
```

Acceptance criteria:

1. Normal backlog read and mutation endpoints require a valid bearer token.
2. Token validation verifies signature, issuer, audience, and expiry.
3. Missing or invalid authentication returns a consistent `401 Unauthorized` response.
4. Authenticated callers without permission receive `403 Forbidden`.
5. Authorization is enforced by the API independently of any web or mobile client.
6. A documented route policy identifies which health endpoints, if any, remain unauthenticated.
7. Authentication configuration and secrets are server-owned and cannot be supplied by request data.
8. Behavior tests cover anonymous, invalid-token, insufficient-permission, and authorized requests.
9. Local development and future EKS configuration are documented.
10. The selected identity provider, claims, and role mapping are recorded in an ADR or security contract before implementation is considered complete.

Immediate design questions for the next session:

- Which identity provider should issue the tokens?
- Should the first policy use coarse roles such as reader/editor/admin or a smaller initial model?
- Should readiness be authenticated, ingress-restricted, or available only inside the cluster?
- How will local test tokens be issued without weakening production validation?

## Following Story — Deploy the Secured API to EKS

Recommended ID:

```text
deploy-johnny-johnny-api-to-eks
```

Description:

```text
Package and deploy the authenticated Johnny-Johnny API to EKS behind HTTPS with Kubernetes health probes, server-owned secrets, controlled network exposure, and observable runtime behavior.
```

Acceptance criteria should include:

- the container starts with `jj serve --host 0.0.0.0 --port 8000`
- a ClusterIP Service reaches the pod on port 8000
- liveness and readiness probes use the documented health endpoints
- external traffic is exposed only through HTTPS ingress
- API authentication is enforced before backlog routes are publicly reachable
- database and provider credentials are supplied through deployment secret management
- PostgreSQL is not made publicly reachable as part of the deployment
- logs include request identity/correlation information without leaking credentials
- deployment and rollback are reproducible

The owning epic should be selected according to the capability improved, not merely the repository changed. Confirm whether this belongs under an existing deployment, release, or dogfooding capability before creating it.

## Following Story — Synchronize GitHub Events into PostgreSQL

Recommended ID:

```text
synchronize-github-project-events-to-canonical-backlog
```

Recommended capability/epic:

```text
Backlog as Code Synchronization
```

Description:

```text
Receive authenticated GitHub webhook deliveries and synchronize authoritative GitHub Project and issue changes into the canonical PostgreSQL backlog without treating webhook payloads as trusted canonical state.
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
- webhook authentication remains separate from human OAuth/OIDC authentication

## Story Order

```text
expose-backlog-workflows-through-rest-api             Done
secure-backlog-rest-api                               Next
deploy-johnny-johnny-api-to-eks                       Following
synchronize-github-project-events-to-canonical-backlog Following
```

The future UI decision does not alter this order. Responsive Next.js and native iPhone clients both depend on the same secured backend.
