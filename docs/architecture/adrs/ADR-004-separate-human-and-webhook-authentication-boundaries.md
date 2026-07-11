# ADR-004: Separate Human and Webhook Authentication Boundaries

**Status:** Accepted; human/API boundary implemented  
**Date:** July 10, 2026

## Context

Johnny-Johnny exposes PostgreSQL-backed backlog workflows through FastAPI. The API will serve browser, mobile, CLI-adjacent, and automation clients. It will also receive inbound GitHub webhook deliveries in a later story.

Human-facing API clients and GitHub webhook deliveries establish trust differently:

- people and normal API clients authenticate through an OAuth 2.0/OpenID Connect provider
- GitHub authenticates webhook deliveries by signing each payload with a shared webhook secret

Treating these as one authentication flow would either force an unsupported OAuth model onto GitHub webhooks or weaken the normal API boundary.

## Decision

Johnny-Johnny maintains two explicit authentication boundaries.

### Human-facing and normal REST API

Normal backlog and operational endpoints require Auth0 bearer access tokens. ADR-005 defines and records the implemented issuer, token-validation, permission, and route policy.

The API, not the UI, is responsible for:

- validating the token signature, issuer, audience, time claims, and subject
- enforcing route permissions from the OAuth `scope` claim
- returning `401 Unauthorized` for missing or invalid authentication
- returning `403 Forbidden` when an authenticated identity lacks permission

A browser UI or native mobile application may initiate an interactive login flow, but neither client is the security perimeter. M2M clients use the same protected API with an appropriate client grant.

Liveness and readiness remain public and deliberately minimal. The protected `/api/v1/auth/whoami` endpoint exists only to verify token identity and scopes without invoking PostgreSQL or GitHub.

### GitHub webhook endpoint

The future GitHub webhook endpoint will be publicly reachable over HTTPS and will not participate in the human OAuth/OIDC login flow.

It will authenticate each delivery by:

- reading the raw request body
- verifying GitHub's `X-Hub-Signature-256` HMAC-SHA256 signature with a server-owned webhook secret
- rejecting missing or invalid signatures before processing the event
- using `X-GitHub-Delivery` as the delivery identity for idempotency and duplicate detection

The shared secret is never accepted from request data and is not sent in the webhook payload.

After accepting a verified delivery, Johnny-Johnny may use a separately configured GitHub App installation token or provider credential when calling the GitHub API. Inbound verification credentials and outbound provider credentials are independent.

## Consequences

- The normal REST surface is secured before public EKS deployment.
- GitHub will be able to reach one narrowly scoped public endpoint without receiving a human access token.
- Browser, mobile, M2M, and automation clients can share one secured backend contract.
- Route exposure explicitly distinguishes normal API traffic, public probes, and future webhook traffic.
- HTTPS, secret management, replay/idempotency protection, structured logging, and auditability remain required even when authentication succeeds.
- The webhook story must not reuse the Auth0 dependency or accept access tokens as a substitute for signature verification.

## Deployment Sequence

1. ~~Secure the existing REST API with OAuth/OIDC and authorization.~~ Implemented with Auth0 and scope authorization.
2. Deploy the secured service to EKS behind HTTPS.
3. Add the signed GitHub webhook endpoint and provider-to-canonical synchronization.

## Related Decisions

- ADR-001: PostgreSQL is canonical backlog runtime state.
- ADR-002: provider synchronization has explicit cross-boundary consistency behavior.
- ADR-003: REST is a peer adapter over shared application workflows.
- ADR-005: Auth0 access-token validation and scope-based authorization.
