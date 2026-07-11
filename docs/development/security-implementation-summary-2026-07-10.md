# Auth0 API Security Implementation Summary

**Date:** July 10, 2026  
**Story:** `secure-backlog-rest-api`  
**Status:** Implemented and behavior-tested  
**Next story:** `deploy-johnny-johnny-api-to-eks`

## Summary

Johnny-Johnny's FastAPI adapter now authenticates Auth0 access tokens and authorizes every backlog route before shared application workflow dispatch.

The implementation remains domain-first:

```text
HTTP bearer/security dependency
  -> authenticated principal + scopes
  -> route authorization
  -> unchanged application workflow
  -> unchanged canonical domain
```

Auth0 is confined to the presentation/security boundary. PostgreSQL remains canonical backlog state, and GitHub remains a provider projection.

## Implemented Behavior

### Token validation

- Auth0 issuer and audience are mandatory server configuration.
- Only `RS256` access tokens are accepted.
- Public keys are selected from the configured tenant JWKS.
- Signature, issuer, audience, `exp`, `iat`, optional `nbf`, and `sub` are validated.
- Tokens require a `kid` header.
- Token-controlled `jku`, `x5u`, and unsupported `crit` headers are rejected.
- Auth0 default (`azp`) and RFC 9068 (`client_id`) profiles are supported.
- Missing or invalid tokens return stable `401` errors.
- JWKS connectivity failure for a needed key returns stable `503` behavior.

### Authorization

Implemented scopes:

```text
read:backlogs
write:backlogs
operate:backlogs
admin:backlogs
```

Route mapping:

```text
read/export                    read:backlogs
create/update/move/delete      write:backlogs
reconcile                      operate:backlogs
import/purge                   admin:backlogs
```

Authorization uses only the space-delimited `scope` claim. The optional `permissions` claim does not grant access when `scope` is absent or insufficient.

Dry-run requests require the same permission as confirmed requests.

### Public and diagnostic routes

- `/api/v1/health/live` remains public and minimal.
- `/api/v1/health/ready` remains public and redacts database details and exceptions.
- `/api/v1/auth/whoami` is protected, requires no backlog permission, touches no database, and returns only subject, client ID, and sorted scopes.

### Application startup

`create_app()` is now the FastAPI application factory.

Production construction:

```text
resolve Auth0 settings
  -> create Auth0AccessTokenVerifier
  -> fail closed if required configuration is missing
```

Behavior tests inject a test verifier through the factory. There is no production `AUTH_DISABLED` or equivalent switch.

The CLI server target changed to:

```text
johnny_johnny_agent.api.app:create_app
factory=True
```

## Configuration

Required for REST startup:

```text
AUTH0_DOMAIN
AUTH0_AUDIENCE
```

Optional:

```text
JOHNNY_JOHNNY_API_DOCS_ENABLED=true
AUTH0_CLOCK_SKEW_SECONDS=30
AUTH0_JWKS_TIMEOUT_SECONDS=5
AUTH0_JWKS_CACHE_SECONDS=300
```

A committed `.env.example` now documents the complete server configuration boundary. Auth0 client IDs and client secrets are deliberately absent because they belong to callers.

## Production Files Added

```text
.env.example
src/johnny_johnny_agent/api/security.py
tests/behavior/test_auth0_access_token_validation.py
```

## Production Files Updated

```text
.gitignore
README.md
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

Executed against the applied project:

```bash
PYTHONPATH=src python -m pytest -o addopts='' -q
```

Result:

```text
109 passed, 1 skipped
```

The skipped test requires live GitHub provider access. No Auth0 tenant, PostgreSQL instance, or network call is required for the security behavior suite. Tests also prove fail-closed factory startup, removal of interactive API documentation, and independent permission boundaries in which `admin:backlogs` is not a wildcard.

The locked environment synchronized successfully with PyJWT and cryptography support. Ruff checks passed for the changed security/API code, and the changed documentation's shell examples passed `bash -n`.

## Auth0 Setup Exercise

The root README now includes:

- Auth0 API creation and RS256 selection
- all four permissions
- RBAC and cumulative role guidance
- least-privilege M2M client setup
- secure client-secret prompting
- client-credentials token exchange
- a missing-token `401` check
- a real-token `/api/v1/auth/whoami` check
- a read-scoped PostgreSQL summary call
- bearer headers for the complete endpoint walkthrough

## Risks and Follow-up

- The EKS environment must allow HTTPS egress to Auth0 JWKS and GitHub while keeping PostgreSQL private.
- JWKS outage can affect a request when the needed key is not cached; the API returns `503` rather than accepting an unverifiable token.
- Token lifetime, client grants, role assignments, and credential rotation are Auth0 tenant operations and must be managed deliberately.
- The initial policy is API-wide. Project-level or organization-level authorization can be added later when there is a concrete multi-tenant requirement.
- Request identity should be added to structured logs/audit history without logging bearer tokens or raw claims.
- Future GitHub webhooks remain HMAC-authenticated and must not reuse the Auth0 dependency.

## Next Phase

Implement `deploy-johnny-johnny-api-to-eks` using the contract in:

```text
docs/deployment/eks-fast-testing-loop.md
```

The next phase should add the container, Kubernetes resources, HTTPS ingress, external secret delivery, and a Bash build/push/deploy/rollout/authenticated-smoke loop.
