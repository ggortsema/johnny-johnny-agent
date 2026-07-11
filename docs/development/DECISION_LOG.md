# Decision Log

Version: 1.0

Purpose:
Capture important engineering and workflow decisions that are too small for an ADR but too valuable to lose.

## Template

Date:
Decision:
Reason:
Supersedes:
Related Story:

---

## 2026-07-08

Decision:
Replace complete methods/functions instead of whole files during AI collaboration.

Reason:
Files have grown large while complete method replacement remains safe and reviewable.

---

## 2026-07-08

Decision:
List commands use a shared table format.

Reason:
Provides a consistent CLI experience.

---

## 2026-07-08

Decision:
Support include and exclude filtering.

Reason:
Common workflow is 'show me everything except Done.'
---

## 2026-07-10

Decision:
Remove the legacy `jj backlog publish` Markdown-to-GitHub workflow. Keep `jj backlog pull` as a provider diagnostic. Defer `jj backlog generate` migration and rename until durable, rate-limited provider reconciliation is implemented; its future replacement will import a GitHub Project directly into PostgreSQL without using YAML as an intermediary.

Reason:
`publish` bypassed the canonical PostgreSQL model and the current reconciliation workflow. Migrating `generate` now would couple provider import to the same large-mutation reliability problem already captured by the durable reconciliation ADR.

Related Story:
implement-postgres-backed-canonical-backlog-persistence

---

## 2026-07-10 — PostgreSQL Runtime Canonical State

Decision:
Use PostgreSQL as the canonical runtime backlog store. Keep YAML only for import, export, backup, migration, validation, and human inspection. Migrated commands must not use YAML as an intermediary.

Reason:
Server mode, REST, webhooks, concurrency, audit history, and multiple provider projections require durable transactional state.

Related ADR:
`ADR-001-postgresql-canonical-backlog-runtime.md`

---

## 2026-07-10 — Intentional Breaking CLI Migration

Decision:
Replace YAML-backed commands one at a time rather than preserving parallel legacy commands. Runtime commands select canonical projects from PostgreSQL using provider, provider account, and stored project title.

Reason:
Parallel persistence paths would create ambiguous behavior and ongoing compatibility cost.

---

## 2026-07-10 — Targeted Provider Synchronization

Decision:
Confirmed create, update, move, and delete workflows must synchronize the targeted GitHub projection before reporting success. Use PostgreSQL rollback, provider compensation, idempotent retry, and explicit consistency errors because GitHub and PostgreSQL cannot share an ACID transaction.

Reason:
Users expect CLI/API mutations to appear in GitHub immediately, but a full-project reconcile is unnecessary and can trigger provider limits.

Related ADR:
`ADR-002-targeted-provider-synchronization.md`

---

## 2026-07-10 — Explicit Provider Project Binding

Decision:
`--project` selects the stored `provider_projects` row. Reconcile and targeted mutations use the external provider ID stored on that row and never silently rebind by searching GitHub project titles.

Reason:
Implicit rebinding caused a sandbox epic to be added to the wrong GitHub Project when copied metadata referenced the production project.

---

## 2026-07-10 — Bounded and Full Projection Operations

Decision:
Support both safe bounded execution and explicit `--all` execution for reconcile and purge. Reconcile budgets provider operations; purge budgets issues.

Reason:
Bounded execution protects against provider limits, while `--all` supports unattended or disposable-environment workflows without requiring manual babysitting.


---

## 2026-07-10 — REST as a Peer Adapter

Decision:
Expose backlog behavior through a versioned FastAPI adapter at `/api/v1`. REST handlers import the same PostgreSQL-backed application workflows used by the CLI and never shell out to `jj`.

Reason:
CLI and server mode must preserve one set of domain, persistence, provider-synchronization, and failure semantics rather than creating parallel implementations.

Related Story:
`expose-backlog-workflows-through-rest-api`

---

## 2026-07-10 — Explicit REST Mutation Modes

Decision:
Require every REST mutation to declare `mode: dry-run` or `mode: confirmed`. Reconcile and purge use the same bounded/default/full scope rules as the CLI. YAML import carries mode in the query string because its body is the YAML document.

Reason:
Mutation intent must be explicit and machine-readable. Preview and committing behavior should not depend on HTTP-method inference or hidden defaults.

Related Story:
`expose-backlog-workflows-through-rest-api`

---

## 2026-07-10 — Server-Owned Database Configuration

Decision:
Do not accept `DATABASE_URL` through REST requests. The API server resolves database connectivity from its own environment. Provider and provider-account selection remain request parameters because they identify canonical backlog location rather than infrastructure credentials.

Reason:
Database topology and credentials are deployment concerns and should not cross the HTTP trust boundary.

Related Story:
`expose-backlog-workflows-through-rest-api`

---

## 2026-07-10 — Separate Human and Webhook Authentication

Decision:
Secure normal REST endpoints with OAuth 2.0/OpenID Connect bearer-token validation and API-side authorization. Authenticate inbound GitHub webhook deliveries separately by verifying the HMAC-SHA256 payload signature with a server-owned webhook secret and using the GitHub delivery ID for idempotency.

Reason:
Interactive users and GitHub webhook deliveries use different supported trust mechanisms. The UI must not become the security perimeter, and GitHub does not send a human OAuth token with webhook requests.

Related ADR:
`ADR-004-separate-human-and-webhook-authentication-boundaries.md`

---

## 2026-07-10 — Security Before Public EKS Deployment

Decision:
Complete the next work in this order: secure the existing REST API, deploy the secured service to EKS over HTTPS, then implement inbound GitHub synchronization.

Reason:
GitHub requires a reachable HTTPS endpoint for live webhook delivery, but the existing backlog API must not be exposed publicly before authentication and authorization are enforced.

---

## 2026-07-10 — Shared Backend for Web and Native Clients

Decision:
Treat a responsive Next.js UI and a future native iPhone application as peer clients of the same secured REST and AI APIs. Prefer the web UI as the first visual control room; defer native implementation until speech, Siri, Action Button, notification, or other iOS integrations provide concrete value.

Reason:
The web client can exercise backlog, chat, review, and initial microphone workflows quickly. Native iOS should be introduced for capabilities unique to the operating system rather than creating a second backend contract.

---

## 2026-07-10 — Auth0 as the Initial API Identity Provider

Decision:
Use Auth0 as the initial OAuth 2.0/OpenID Connect provider. Configure Johnny-Johnny as an audience-specific resource server that validates RS256 access tokens against the issuer JWKS. Keep Auth0 integration in the HTTP security boundary rather than the canonical domain or backlog workflows.

Reason:
Auth0 supports the planned browser, native, and M2M client types while allowing one independently secured API contract. A standards-based verifier preserves future provider flexibility.

Related ADR:
`ADR-005-auth0-access-token-and-permission-policy.md`

---

## 2026-07-10 — Authorize from OAuth Scopes

Decision:
Enforce `read:backlogs`, `write:backlogs`, `operate:backlogs`, and `admin:backlogs` from the access token's space-delimited `scope` claim. Do not authorize from Auth0 role names or treat the optional `permissions` claim as effective requested scope. Permissions are independent; Auth0 roles should be cumulative.

Reason:
Scopes are the stable resource-server contract across interactive and M2M clients. Using `scope` preserves request down-scoping and avoids coupling route policy to provider administration concepts.

Related Story:
`secure-backlog-rest-api`

---

## 2026-07-10 — Public Minimal Probes and Protected Whoami

Decision:
Keep liveness and readiness public for Kubernetes and load balancers, but return only minimal status. Add `/api/v1/auth/whoami` as a protected token-validation exercise that returns subject, client ID, and scopes without accessing PostgreSQL or echoing raw claims.

Reason:
EKS needs unauthenticated probes, while Auth0 setup needs an endpoint that isolates token and ingress verification from database state. Minimal output avoids exposing infrastructure details.

Related Story:
`secure-backlog-rest-api`

---

## 2026-07-10 — No Runtime Authentication Bypass

Decision:
Do not ship an environment variable that disables API authentication. Build the FastAPI app through a factory and inject a test verifier only in behavior tests. Production startup fails closed when Auth0 domain or audience is absent.

Reason:
A local bypass is a deployment footgun. Dependency injection gives deterministic tests without weakening the production configuration surface.

Related Story:
`secure-backlog-rest-api`
