# API Security, Deployment, and Client Evolution

**Status:** Auth0 security implemented; EKS deployment next  
**Date:** July 10, 2026

## Purpose

Capture the implemented API security boundary, the next EKS deployment phase, the later GitHub webhook boundary, and how future web and iPhone clients share the same backend contract.

## Delivery Sequence

```text
Auth0-secured REST API                    implemented
  -> deploy secured API to EKS over HTTPS next
  -> receive signed GitHub webhooks       planned
  -> synchronize GitHub into PostgreSQL  planned
```

The client choice does not alter this sequence. A Next.js client, a native iPhone client, and M2M automation all call the same authenticated resource server.

## Implemented Auth0 Boundary

```text
client -> Auth0 flow -> audience-specific access token
       -> Authorization: Bearer TOKEN
       -> API validates RS256/JWKS + issuer + audience + time claims
       -> API enforces route scope
       -> shared backlog workflow
```

Server-owned configuration:

```text
AUTH0_DOMAIN
AUTH0_AUDIENCE
AUTH0_CLOCK_SKEW_SECONDS
AUTH0_JWKS_TIMEOUT_SECONDS
AUTH0_JWKS_CACHE_SECONDS
```

The API does not use an Auth0 client secret. Calling applications own their client credentials or interactive flow configuration.

Implemented permissions:

```text
read:backlogs
write:backlogs
operate:backlogs
admin:backlogs
```

Baseline behavior:

- no bearer token: `401 Unauthorized`
- invalid signature, issuer, audience, algorithm, time, or subject: `401 Unauthorized`
- valid identity without required scope: `403 Forbidden`
- valid identity and scope: workflow dispatch
- issuer signing keys unavailable for an uncached key: `503 Service Unavailable`

Authorization uses `scope`, not Auth0 role names and not the optional `permissions` claim. Roles are cumulative Auth0 administration constructs that grant API permissions.

## Public Operational Surface

Kubernetes and load-balancer probes need no bearer token:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
```

Both responses are minimal. Readiness reports only database/schema categories and suppresses exception and connection details.

`GET /api/v1/auth/whoami` is protected but needs no backlog permission. It verifies a real token without touching PostgreSQL or GitHub and returns only subject, client ID, and scopes.

Swagger UI, ReDoc, and OpenAPI can be removed by setting:

```text
JOHNNY_JOHNNY_API_DOCS_ENABLED=false
```

## Local and Container Binding

Local development:

```bash
uv run jj serve --host 127.0.0.1 --port 8000
```

Container or EKS pod:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

Binding to `0.0.0.0` is reachability, not security. Authentication remains mandatory on every protected route regardless of bind address or network placement.

## EKS Deployment Boundary

The next story must preserve and surround the application boundary with:

- an immutable container image
- ECR image publication
- a Deployment that starts `uv run jj serve --host 0.0.0.0 --port 8000`
- a ClusterIP Service
- HTTPS ingress and certificate management
- `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` as non-secret configuration
- `DATABASE_URL` and `GITHUB_TOKEN` from an approved secret delivery mechanism
- liveness and readiness probes on the public minimal endpoints
- a restricted pod/service-account identity
- ingress and egress controls appropriate to PostgreSQL, Auth0 JWKS, and GitHub
- rollout status, logs, and authenticated smoke-test behavior in the fast loop

The deployment loop must never put client secrets, database credentials, GitHub tokens, or bearer tokens in a committed manifest, image layer, command argument, or shell trace.

See `docs/deployment/eks-fast-testing-loop.md` for the contract to implement in the deployment story.

## GitHub Webhook Authentication

GitHub does not use Auth0 when delivering webhooks.

```text
GitHub -> HTTPS webhook endpoint
       -> signed raw payload
       -> HMAC-SHA256 verification
       -> delivery deduplication
       -> provider-to-canonical synchronization
```

The future webhook endpoint uses a server-owned shared secret to verify `X-Hub-Signature-256`. The secret is never transmitted. `X-GitHub-Delivery` provides the delivery identity for idempotency.

Outbound Johnny-Johnny calls to GitHub use a separate provider credential, preferably a GitHub App installation token when that integration is introduced.

The webhook endpoint must not reuse the Auth0 bearer dependency or treat a bearer token as equivalent to a valid GitHub signature.

## Client Roles

### Responsive Next.js web UI

The web application is the likely first visual client and serves as Johnny-Johnny's control room:

- backlog browsing and mutation
- typed conversational interaction
- AI proposal review and explicit confirmation
- reconciliation, webhook, and consistency visibility
- administration and audit history
- browser microphone recording for early voice experiments

It should use an Auth0-supported interactive flow, request only the scopes needed for the current action, and call the same API contract documented in OpenAPI.

### Native iPhone application

A native client becomes valuable when Johnny-Johnny needs deeper operating-system integration:

- faster voice capture
- native speech processing
- Siri, Shortcuts, widgets, Spotlight, and Action Button integration
- richer notifications and quick approvals
- Keychain and Face ID/Touch ID integration

It remains another adapter over the same Auth0-secured REST and AI APIs. It does not require a different canonical model or synchronization architecture.

### M2M and automation clients

Local smoke tests, CI jobs, and trusted backend automation use Auth0 Machine-to-Machine applications. Each client grant is a least-privilege ceiling. Administrative smoke clients should be temporary or tightly controlled, and their credentials must be rotated or revoked after use.

## Provisional Client Direction

Deploy the secured backend first. A responsive Next.js control-room UI remains the preferred first visual client because it can exercise backlog management, conversational workflows, and human-in-the-loop approval quickly. Build a dedicated iPhone app when native speech and OS integrations provide concrete value that the browser cannot supply reliably.

The immediate backlog remains EKS deployment followed by signed GitHub webhook synchronization.
