# API Security, Deployment, and Client Evolution

**Status:** Planned evolution
**Date:** July 10, 2026

## Purpose

Capture the agreed sequence for moving the completed local REST API into an authenticated deployed service and then adding inbound GitHub synchronization. Also record how future web and iPhone clients fit the same backend boundary.

## Agreed Sequence

```text
secure existing REST API with OAuth/OIDC
  -> deploy secured API to EKS over HTTPS
  -> receive and authenticate GitHub webhooks
  -> synchronize authoritative GitHub state into PostgreSQL
```

The UI decision does not alter this sequence. A Next.js client and a native iPhone client both call the same authenticated backend.

## Local and Container Binding

Local development remains loopback-only while authentication is absent:

```bash
uv run jj serve --host 127.0.0.1 --port 8000
```

Inside a container or EKS pod, the process must bind to the pod network interface:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

Binding to `0.0.0.0` is reachability, not security. Access is controlled by the Kubernetes Service, ingress, TLS, network policy, and application authentication/authorization.

## Human API Authentication

Normal API clients use OAuth 2.0/OpenID Connect:

```text
user -> client login -> identity provider -> bearer token
     -> Johnny-Johnny API validates token -> authorization policy -> workflow
```

Expected baseline behavior:

- missing or invalid token: `401 Unauthorized`
- valid identity without permission: `403 Forbidden`
- valid identity with permission: workflow executes

The API enforces this policy independently of any browser or native UI.

## GitHub Webhook Authentication

GitHub does not use the human OAuth flow when delivering webhooks.

```text
GitHub -> HTTPS webhook endpoint
       -> signed raw payload
       -> HMAC-SHA256 verification
       -> delivery deduplication
       -> provider-to-canonical synchronization
```

The webhook endpoint uses a server-owned shared secret to verify `X-Hub-Signature-256`. The secret itself is never transmitted. `X-GitHub-Delivery` provides a stable delivery identifier for idempotency.

Outbound Johnny-Johnny calls to the GitHub API use a separate provider credential, preferably a GitHub App installation token when that integration is introduced.

## Client Roles

### Responsive Next.js web UI

The web application is the likely first visual client and serves as Johnny-Johnny's control room:

- backlog browsing and mutation
- typed conversational interaction
- AI proposal review and explicit confirmation
- reconciliation, webhook, and consistency visibility
- administration and audit history
- browser microphone recording for early voice experiments

A responsive web UI can run on desktop and mobile and can later become an installable PWA.

### Native iPhone application

A native client becomes valuable when Johnny-Johnny needs deeper operating-system integration:

- faster voice capture
- native speech processing
- Siri, Shortcuts, widgets, Spotlight, and Action Button integration
- richer notifications and quick approvals
- Keychain and Face ID/Touch ID integration

The native app remains another adapter over the same secured REST and AI APIs. It does not require a different canonical model or synchronization architecture.

## Provisional Client Direction

Build the secured backend first. A responsive Next.js control-room UI is the preferred first client because it exercises backlog management, conversational workflows, and human-in-the-loop approval quickly. Build a dedicated iPhone app when native speech and OS integrations provide concrete value that the browser cannot supply reliably.

This direction is intentionally not yet a committed implementation story; the immediate backlog remains API security, EKS deployment, and GitHub synchronization.
