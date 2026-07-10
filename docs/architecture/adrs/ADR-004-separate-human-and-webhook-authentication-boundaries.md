# ADR-004: Separate Human and Webhook Authentication Boundaries

**Status:** Accepted
**Date:** July 10, 2026

## Context

Johnny-Johnny now exposes PostgreSQL-backed backlog workflows through FastAPI. The API will eventually serve browser, mobile, CLI-adjacent, and automation clients. It will also receive inbound GitHub webhook deliveries.

Human-facing API clients and GitHub webhook deliveries establish trust differently:

- people and interactive clients authenticate through an identity provider
- GitHub authenticates webhook deliveries by signing each payload with a shared webhook secret

Treating these as one authentication flow would either force an unsupported OAuth model onto GitHub webhooks or weaken the normal API boundary.

## Decision

Johnny-Johnny will maintain two explicit authentication boundaries.

### Human-facing REST API

Normal backlog and operational endpoints will require OAuth 2.0/OpenID Connect bearer tokens before the service is exposed publicly.

The API, not the UI, is responsible for:

- validating the token signature, issuer, audience, and expiry
- mapping the authenticated subject to application authorization policy
- returning `401 Unauthorized` for missing or invalid authentication
- returning `403 Forbidden` when an authenticated identity lacks permission

A browser UI or native mobile application may initiate the login flow, but neither client is the security perimeter.

The identity provider, exact claims, role model, and route-by-route authorization policy are intentionally deferred to the security story.

### GitHub webhook endpoint

The GitHub webhook endpoint will be publicly reachable over HTTPS and will not participate in the human OAuth/OIDC login flow.

It will authenticate each delivery by:

- reading the raw request body
- verifying GitHub's `X-Hub-Signature-256` HMAC-SHA256 signature with a server-owned webhook secret
- rejecting missing or invalid signatures before processing the event
- using `X-GitHub-Delivery` as the delivery identity for idempotency and duplicate detection

The shared secret is never accepted from request data and is not sent in the webhook payload.

After accepting a verified delivery, Johnny-Johnny may use its separately configured GitHub App installation token or provider credential when calling the GitHub API.

## Consequences

- The existing REST API can be secured and tested before the webhook endpoint exists.
- GitHub can reach one narrowly scoped public endpoint without receiving a human access token.
- Browser and iPhone clients can share one secured backend contract.
- Route exposure must distinguish normal API traffic, health checks, and webhook traffic.
- HTTPS, secret management, replay/idempotency protection, structured logging, and auditability remain required even though the webhook uses a valid signature.

## Deployment Sequence

1. Secure the existing REST API with OAuth/OIDC and authorization.
2. Deploy the secured service to EKS behind HTTPS.
3. Add the signed GitHub webhook endpoint and provider-to-canonical synchronization.

## Related Decisions

- ADR-001: PostgreSQL is canonical backlog runtime state.
- ADR-002: provider synchronization has explicit cross-boundary consistency behavior.
- ADR-003: REST is a peer adapter over shared application workflows.
