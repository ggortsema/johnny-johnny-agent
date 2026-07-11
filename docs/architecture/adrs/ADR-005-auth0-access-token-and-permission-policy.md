# ADR-005: Auth0 Access Tokens and Scope-Based API Authorization

**Status:** Accepted and implemented  
**Date:** July 10, 2026  
**Story:** `secure-backlog-rest-api`

## Context

ADR-004 established separate trust boundaries for human-facing REST traffic and future GitHub webhook delivery. The existing FastAPI adapter now needs a concrete identity provider, token-validation contract, authorization model, route policy, and safe local testing behavior before it can be deployed to EKS.

The API will serve multiple peer clients over time:

- a responsive web client
- a native mobile client
- command-line smoke tests and automation
- potentially other trusted service clients

Authorization must remain an application boundary rather than a UI convention. The provider integration should not leak into the canonical backlog domain or application workflows.

## Decision

### Identity provider

Auth0 is the initial OAuth 2.0/OpenID Connect provider.

The API is implemented as a standards-based OAuth resource server. Auth0-specific configuration and JWKS retrieval remain in the FastAPI security boundary. The domain model and backlog workflows have no Auth0 dependency.

### Token validation

The API accepts bearer access tokens issued for one configured audience and validates:

- RS256 signature using a public key from the configured issuer JWKS
- exact issuer
- configured audience
- expiration and issued-at time
- optional not-before time
- non-empty subject
- a signing-key ID

Only the server-owned `AUTH0_DOMAIN` determines the issuer and JWKS URL. Token-controlled `jku` and `x5u` key sources and unsupported critical headers are rejected. The accepted algorithm is fixed to `RS256`; it is never selected from untrusted token data.

The verifier supports Auth0's default and RFC 9068 access-token profiles by accepting `azp` or `client_id` as client metadata. It does not require application code to know which profile issued the token.

### Authorization claim

The API authorizes from the standard space-delimited OAuth `scope` claim.

The optional Auth0 `permissions` claim is not treated as effective requested scope. When RBAC is enabled, Auth0 computes `scope` from what the client requested and what the subject is allowed to receive. Using `scope` preserves down-scoping and keeps the API policy independent of Auth0 role names.

### Permissions

The Auth0 API defines four permissions:

```text
read:backlogs
write:backlogs
operate:backlogs
admin:backlogs
```

They are independent capabilities:

- `read:backlogs`: summary, list, describe, and export
- `write:backlogs`: create, update, move, and delete targeted items
- `operate:backlogs`: provider reconciliation
- `admin:backlogs`: canonical snapshot import and provider purge

`admin:backlogs` is not a wildcard. Human roles should be cumulative when a person needs several capabilities. Machine-to-Machine client grants should contain only the permissions needed by that client.

### Route policy

| Route class | Policy |
|---|---|
| Liveness | public and minimal |
| Readiness | public and minimal |
| `/api/v1/auth/whoami` | valid access token; no backlog permission |
| Backlog reads/export | `read:backlogs` |
| Targeted mutations | `write:backlogs` |
| Reconciliation | `operate:backlogs` |
| Import/purge | `admin:backlogs` |

Dry-run operations require the same permission as their confirmed form. Preview behavior is not an authorization bypass.

### Probe disclosure

Kubernetes and load-balancer probes remain unauthenticated, but their responses expose only service/version/readiness categories. They do not expose database identity, connection details, schema object names, exception messages, or provider credentials.

### Local testing

There is no production runtime switch that disables authentication.

The FastAPI application is created by an application factory. Behavior tests inject a test verifier through that factory. Production startup constructs the real Auth0 verifier and fails closed when issuer or audience configuration is absent.

A protected `/api/v1/auth/whoami` endpoint returns only subject, client ID, and granted scopes. It allows Auth0 setup to be tested independently of PostgreSQL and GitHub without returning raw claims or tokens.

### Interactive documentation

Swagger UI, ReDoc, and OpenAPI can be enabled or removed through `JOHNNY_JOHNNY_API_DOCS_ENABLED`. When enabled, OpenAPI describes HTTP bearer authentication. Documentation visibility does not relax endpoint authorization.

## Consequences

### Positive

- Every backlog route enforces authentication and authorization before workflow dispatch.
- Auth0 tenant configuration is explicit and can be supplied through EKS configuration and secret mechanisms.
- The verifier remains standards-based enough to evolve without changing domain workflows.
- OAuth scopes form a stable client contract across web, mobile, M2M, and automation clients.
- Public probes remain usable by Kubernetes without becoming an information-disclosure endpoint.
- Local and automated tests do not require a live Auth0 tenant.
- A real Auth0 token can be exercised before database connectivity is involved.

### Costs and limitations

- The API depends on issuer signing keys. A request that requires an uncached key can fail with `503` while the JWKS endpoint is unavailable.
- Scope design and client grants must be maintained in Auth0 as well as documented in the project.
- Client credentials used for smoke testing must be handled and rotated as secrets even though the API itself does not need them.
- The initial route policy is coarse-grained and does not yet restrict access by project, organization, tenant, or resource owner.
- Access-token revocation behavior remains bounded by token lifetime and issuer-key behavior; deployment policy should use appropriately short token lifetimes.

## Alternatives Rejected

### API keys shared with users

Rejected because a shared API key does not provide subject identity, standards-based client flows, or permission-bearing tokens suitable for web and mobile clients.

### Auth0 role names in application code

Rejected because role names are provider administration concepts and make authorization less portable. Roles grant API permissions; the API enforces scopes.

### Authorize from the `permissions` claim

Rejected because that claim can represent all permissions assigned to a user rather than the intersection requested for a specific token. The `scope` claim preserves OAuth down-scoping.

### HS256 with an Auth0 client secret

Rejected because it would share signing material with the API and confuse application credentials with resource-server verification. RS256 permits public-key validation through JWKS.

### Local “disable auth” environment variable

Rejected because it creates a deployment footgun. Tests inject a verifier at construction time instead of shipping a bypass in production configuration.

### Authenticate readiness probes

Rejected for the first EKS deployment because it complicates standard health checks. Minimal probe output provides the needed operational signal without disclosing detailed runtime state.

## Related Decisions

- ADR-001: PostgreSQL is canonical backlog runtime state.
- ADR-002: provider synchronization has explicit cross-boundary consistency behavior.
- ADR-003: REST is a peer adapter over shared application workflows.
- ADR-004: human REST and GitHub webhook authentication are separate boundaries.
