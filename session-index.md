# Session Index

**Date:** July 10, 2026
**Project:** Johnny-Johnny Agent
**Project Version:** 0.1.0
**Git Branch:** dev
**Completed Story:** `expose-backlog-workflows-through-rest-api`
**Next Story:** `secure-backlog-rest-api`
**Following Stories:** `deploy-johnny-johnny-api`, `synchronize-github-project-events-to-canonical-backlog`

## Session Summary

This session completed and validated the first full FastAPI adapter over Johnny-Johnny's PostgreSQL-backed backlog workflows.

The applied project test suite completed with:

```text
87 passed
```

The API was started locally and most of the README curl walkthrough was exercised successfully. REST purge and reconciliation were intentionally not executed live because they are broad or destructive provider workflows; their HTTP dispatch and response behavior remain covered by automated endpoint tests.

The session then established the next architectural sequence:

```text
secure the existing REST API with OAuth/OIDC
  -> deploy the secured API to a reachable HTTPS runtime
  -> implement signed GitHub webhook synchronization
```

Human-facing REST authentication and GitHub webhook authentication are separate trust boundaries. Browser and native mobile clients will authenticate through OAuth/OIDC. GitHub webhook deliveries will use HMAC-SHA256 request-signature verification with a server-owned shared secret.

Johnny-Johnny will be implemented as a provider-neutral OIDC resource server rather than acting as its own identity provider. Auth0 is the recommended first managed provider because it offers low-friction support for FastAPI, Next.js, and native iOS while leaving Johnny-Johnny deployable on a laptop, EC2, ECS, EKS, another cloud, or an on-premises host. The native iPhone application is a primary product client and intended main controller, especially for voice-driven AI interaction; it is not a speculative later possibility.

## Story Completed

### `expose-backlog-workflows-through-rest-api`

Completed behavior includes:

- versioned FastAPI routes under `/api/v1`
- liveness and PostgreSQL/schema readiness
- backlog summary, epic list, issue list, and item detail reads
- create epic, create issue, update, move, and delete workflows
- reconciliation and purge workflows
- raw YAML import and YAML export
- direct reuse of application workflows with no CLI subprocess invocation
- typed request and response contracts
- explicit `dry-run` and `confirmed` mutation modes
- stable HTTP error envelopes
- generated OpenAPI, Swagger UI, and ReDoc
- complete README curl examples
- endpoint behavior tests and full local suite verification

The canonical completion command and comment are recorded in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Current Story

No implementation story remains in progress at session close. The REST story should be confirmed as Done in the canonical backlog before beginning the next story.

## Next Recommended Story

### `secure-backlog-rest-api`

Secure the existing FastAPI surface with OAuth 2.0/OpenID Connect bearer-token validation and API-side authorization before making the service publicly reachable.

The next session should begin with design rather than code:

1. confirm Auth0 as the first managed identity provider unless design review finds a blocker
2. define a provider-neutral OIDC configuration contract for issuer, audience, client IDs, and claims
3. define token issuer, audience, and claims
4. define the initial authorization model
5. define route policy for liveness and readiness
6. define safe local authentication/testing behavior
7. define native iPhone Authorization Code with PKCE requirements as a first-class client flow

The proposed description and acceptance criteria are recorded in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Following Story Sequence

### `deploy-johnny-johnny-api`

Deploy only after API authentication is enforced. The deployment design must support EC2, containers, Kubernetes/EKS, and other runtimes through configuration rather than application rewrites.

When running inside a container or Kubernetes pod, start the API with:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

For a directly hosted process, bind to the address appropriate for that host and control exposure through HTTPS, firewall/security-group rules, reverse-proxy configuration, and application authorization.

### `synchronize-github-project-events-to-canonical-backlog`

After a secured, publicly reachable HTTPS endpoint exists, add the public GitHub webhook route, HMAC signature verification, delivery idempotency, and provider-to-canonical synchronization.

## Architectural Decisions

1. Normal REST endpoints will use OAuth 2.0/OpenID Connect authentication and API-side authorization.
2. The UI is not the security perimeter; every client must call an independently secured API.
3. GitHub webhook delivery authentication is separate from human OAuth/OIDC authentication.
4. GitHub webhook requests will be verified using `X-Hub-Signature-256` over the raw body with a server-owned secret.
5. `X-GitHub-Delivery` will identify deliveries for duplicate detection and idempotency.
6. Outbound Johnny-Johnny calls to GitHub use a separate provider credential from inbound webhook verification.
7. The secured API must be implemented before any public deployment.
8. A publicly reachable HTTPS deployment must exist before end-to-end GitHub webhook testing.
9. The native iPhone application is a first-class primary client and the intended main Johnny-Johnny controller, especially for voice capture, AI commands, notifications, and approvals.
10. A responsive Next.js application is a complementary web control room for administration, visualization, detailed review, and troubleshooting; it is not a prerequisite for the native mobile controller.
11. Johnny-Johnny will be an OIDC resource server, not its own OAuth/OIDC identity provider.
12. Auth0 is the recommended first managed provider, while authentication code and configuration must remain standards-based and provider-neutral.
13. Identity-provider choice must not couple Johnny-Johnny to Docker, EKS, AWS, or any other deployment target.

See:

```text
docs/architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md
docs/architecture/api-security-deployment-and-client-evolution.md
```

## Engineering Artifacts Created

```text
docs/architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md
docs/architecture/api-security-deployment-and-client-evolution.md
```

## Engineering Artifacts Updated

```text
README.md
docs/api/backlog-rest-api.md
docs/architecture/canonical-backlog-runtime-architecture.md
docs/development/DECISION_LOG.md
docs/development/README.md
docs/development/backlog-session-update-plan-2026-07-10.md
docs/development/commands-left-off.txt
docs/development/rest-api-implementation-summary-2026-07-10.md
docs/development/session-index.md
```

## Production Files Changed During the Completed REST Story

Added:

```text
src/johnny_johnny_agent/api/errors.py
src/johnny_johnny_agent/api/models.py
src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/api/serialization.py
tests/behavior/test_backlog_rest_api.py
```

Updated:

```text
src/johnny_johnny_agent/api/app.py
src/johnny_johnny_agent/capabilities/backlog_persistence/workflow.py
src/johnny_johnny_agent/capabilities/backlog_sync/yaml_loader.py
src/johnny_johnny_agent/capabilities/backlog_sync/yaml_writer.py
```

This closure pass changed documentation only.

## Verification

```text
Applied-project behavior suite: 87 passed
OpenAPI surface: 13 paths / 15 operations
Local API: started successfully
Liveness/readiness: exercised successfully
README curl walkthrough: most endpoint classes exercised successfully
REST purge: not live-tested
REST reconciliation: not live-tested
```

The persistence migration's earlier full CLI reconciliation was already confirmed successful and produced the expected GitHub state. The remaining gap is specifically live invocation of the REST wrappers for purge and reconciliation.

## Bugs and Risks Discovered

### Container loopback binding hazard

Starting the process with `--host 127.0.0.1` inside a container or pod would bind only to container loopback, so an external service could not reach it. Containerized startup must use `--host 0.0.0.0`; directly hosted processes should bind according to their network boundary.

### Public exposure before authentication

The current REST API has no authentication middleware. Binding it publicly before the security story would expose backlog reads and mutations. It must remain loopback-only or on a trusted private boundary until OAuth/OIDC and authorization are implemented.

No new domain, persistence, or provider-synchronization implementation bug was discovered during this session.

## Lessons Learned

- Reachability and authentication are separate concerns; `0.0.0.0` is necessary in a pod but does not secure the service.
- OAuth/OIDC is appropriate for people and interactive clients, not GitHub webhook delivery authentication.
- Webhook signature verification authenticates the provider request without transmitting the shared secret.
- The browser UI and native iPhone app should not create separate backend contracts.
- The native iPhone app is the primary controller envisioned for Johnny-Johnny, particularly for speech-driven interaction with the AI layer.
- The responsive web UI remains valuable as a control room, but it complements rather than precedes or justifies the native app.
- A managed OIDC provider can remain completely independent of where Johnny-Johnny is deployed.
- GraphQL, search indexing, and client-side filtering solve different problems; the current backlog size does not justify additional query infrastructure.

## Outstanding Work

1. Confirm the REST story is marked Done in the canonical backlog.
2. Create or activate `secure-backlog-rest-api` under the capability that owns platform/API security.
3. Confirm Auth0 as the initial managed identity provider and preserve a provider-neutral OIDC boundary.
4. Define both native iPhone Authorization Code with PKCE and web-client login requirements.
5. Implement and behavior-test OAuth/OIDC authentication.
6. Deploy the secured API to the selected runtime behind HTTPS; EKS remains one supported option rather than an architectural requirement.
7. Implement authenticated GitHub webhook ingestion and GitHub-to-PostgreSQL synchronization.
8. Live-test REST reconciliation against the disposable sandbox when desired.
9. Live-test REST purge only when intentionally proving destruction and reconstruction.
10. Continue deferred persistence work: durable operation runs, retry/backoff, throttling, explicit provider-project rebinding, and replacement of `generate`.
11. Move PostgreSQL behind private networking and rotate/remove the temporary public development exposure.

## Category Review

- **ADRs:** Updated; ADR-004 created for separate human and webhook authentication boundaries.
- **Architecture documentation:** Updated; security, EKS binding, webhook flow, and client evolution captured.
- **Specifications:** Reviewed; no domain or YAML specification change was required.
- **Database documentation:** Reviewed; no schema or persistence decision changed.
- **Engineering Principles:** Reviewed; existing domain-first, canonical-state, boundary-consistency, and durable-knowledge principles already cover this session.
- **Working Agreement:** Reviewed; no process change was required.
- **AI Collaboration documentation:** Reviewed; no collaboration-process change was required.
- **Behavior tests:** Reviewed; no closure-only test change was required. Applied project result is `87 passed`.
- **Backlog:** Updated through the durable backlog update plan; canonical mutation remains to be run through `jj` if not already applied.
- **Other project documentation:** README, REST contract, implementation summary, decision log, and commands-left-off updated.

## Files Likely Needed Next Session

```text
README.md
pyproject.toml
src/johnny_johnny_agent/api/app.py
src/johnny_johnny_agent/api/errors.py
src/johnny_johnny_agent/api/models.py
src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/config.py
tests/behavior/test_backlog_rest_api.py
docs/api/backlog-rest-api.md
docs/architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md
docs/architecture/api-security-deployment-and-client-evolution.md
docs/development/backlog-session-update-plan-2026-07-10.md
```

Depending on the selected identity provider, the next session may also need deployment configuration, JWKS/token fixtures, and any existing platform-security documentation.

## Immediate First Task

Confirm the REST story status:

```bash
uv run jj backlog describe \
  expose-backlog-workflows-through-rest-api \
  --project "Johnny-Johnny Backlog Persistence Sandbox"
```

If it is not Done, apply the completion command in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

Then begin `secure-backlog-rest-api` by confirming Auth0 as the initial managed provider, defining the provider-neutral OIDC configuration contract, and documenting route authorization plus native iPhone PKCE behavior before changing FastAPI code.
