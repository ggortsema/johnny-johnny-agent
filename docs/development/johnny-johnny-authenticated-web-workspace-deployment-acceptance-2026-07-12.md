# Johnny-Johnny Authenticated Web Workspace Deployment Acceptance

**Date:** July 12, 2026  
**UI Version:** 0.2.0  
**Deployment target:** EKS  
**Public origin:** `https://johnny-johnny.mycroftai.org`

## Summary

The rebuilt Johnny-Johnny web workspace was integrated into the canonical UI repository, the companion assistant changes were integrated into the canonical agent repository, and both applications were deployed successfully to EKS behind the existing HTTPS Application Load Balancer.

The deployed path is:

```text
https://johnny-johnny.mycroftai.org/
→ johnny-johnny-ui

https://johnny-johnny.mycroftai.org/api/v1/*
→ johnny-johnny-agent
```

The web UI was validated successfully through Auth0 login and the authenticated workspace.

## Completed Work

### UI

- Replaced the previous UI direction with the new authenticated workspace.
- Added public landing page.
- Added Auth0 SPA login using Authorization Code Flow with PKCE.
- Added authenticated Assistant, Documentation, and Git workspaces.
- Added server-provided model selection.
- Added browser voice input and response speech support.
- Added responsive desktop and mobile layouts.
- Added build-time ADR import and searchable documentation catalog.
- Added EKS Dockerfile, Kubernetes manifests, and deployment script.
- Added public runtime configuration endpoint.
- Added health endpoint and same-origin API proxy.
- Regenerated `package-lock.json` against the public npm registry.
- Verified four UI tests.
- Verified production Next.js build.
- Verified import of thirty ADRs.
- Verified zero reported npm vulnerabilities at installation time.

### Agent companion changes

- Added authenticated assistant model catalog support.
- Added selectable-model support with a server-owned allowlist.
- Preserved the default model.
- Added controlled errors for unsupported model selection.
- Updated API, documentation, tests, and EKS manifests.
- Verified 148 agent tests passed.

### Auth0

- Created a Single Page Application named `Johnny-Johnny UI`.
- Configured callback, logout, and web origins.
- Granted the SPA access to all currently defined Johnny-Johnny API permissions.
- Enabled RBAC on the Johnny-Johnny API.
- Enabled permissions in access tokens.
- Created a Johnny-Johnny Administrator role.
- Assigned API permissions to the role.
- Created a human login user and assigned the administrator role.
- Validated the deployed UI with the correct SPA Client ID.

## Deployment Acceptance

The UI deployment completed successfully and reported:

```text
UI: https://johnny-johnny.mycroftai.org/
Agent API: https://johnny-johnny.mycroftai.org/api/v1/
```

The user then validated:

- the public landing page;
- Auth0 login;
- callback to the application;
- the authenticated workspace;
- the mobile-responsive web layout;
- the overall visual quality and usability.

## Bugs Found and Resolved

### Private npm registry references

The delivered `package-lock.json` referenced an internal package proxy.

Resolution:

- removed the generated lockfile and `node_modules`;
- reinstalled from the public npm registry;
- regenerated `package-lock.json`;
- verified no internal-registry references remained.

### Docker non-root user validation

The image declared a named user:

```dockerfile
USER nextjs
```

The Kubernetes workload used `runAsNonRoot: true`, and kubelet could not verify that the named user was non-root.

Resolution:

```dockerfile
USER 1001
```

The deployment then started successfully.

### Stale shell Auth0 Client ID

The deploy script used an environment-variable override:

```bash
AUTH0_CLIENT_ID="${AUTH0_CLIENT_ID:-<default>}"
```

A stale exported Client ID silently overrode the intended SPA Client ID, causing callback mismatch errors.

Resolution for this deployment:

- unset the stale shell variable;
- redeployed the UI;
- verified the public `/runtime-config` returned the expected Client ID.

Long-term decision:

- local deployment scripts must be deterministic and self-contained;
- stale shell state must not silently alter production configuration;
- StyxCD integration must use explicit deployment inputs.

### Stale authenticated smoke-test token

The agent deployment script reused a stale `ACCESS_TOKEN`, causing an authenticated smoke test to fail with HTTP 401.

Temporary resolution:

- unset stale access-token variables.

Long-term decision:

- the deployment script should mint a fresh short-lived M2M token for authenticated smoke tests;
- the token must be obtained securely and discarded after validation.

### Temporary ALB 504 during transition

The shared ingress routed `/` to the old UI Service while its Deployment was scaled to zero. During the transition, public checks returned 504 even though the agent pod and Service were healthy.

Validation showed:

- agent pod healthy;
- agent Service endpoint present;
- in-cluster liveness returned HTTP 200;
- shared ingress routes were structurally correct.

Deploying the new UI restored healthy targets and completed the shared-ingress transition.

## Architectural Decisions

- UI and agent remain separate Kubernetes workloads.
- They share one public hostname and one ALB ingress.
- `/api/v1` routes to the agent.
- `/` routes to the UI.
- Auth0 SPA authentication uses PKCE and no client secret.
- Public SPA configuration is not treated as secret material.
- Server-side permissions and model allowlists remain authoritative.
- PostgreSQL remains canonical runtime state.
- The browser remains an interaction adapter.
- Build and deployment paths must not depend on developer-specific filesystem locations.
- Local deployment scripts are the first deployment phase.
- The proven local path will then be moved into StyxCD as a second phase.

## Outstanding Deployment Work

### Phase 1: local deployment hardening

- Remove unsafe stale-shell configuration overrides.
- Add explicit deterministic configuration loading.
- Make agent document acquisition portable.
- Add a wrapper that deploys agent and UI in a defined order.
- Mint a fresh Auth0 M2M token for authenticated smoke tests.
- Improve ALB target-readiness retries and diagnostics.
- Preserve executable script modes in Git.
- Validate both workloads through one local acceptance flow.

### Phase 2: StyxCD EKS path

- Model agent and UI as separate workloads.
- Reproduce the proven build and push behavior.
- Reproduce the shared ingress and certificate configuration.
- Reuse the existing Route 53 record.
- Reproduce rollout checks and smoke tests.
- Prove end-to-end deployment through StyxCD.

## Next Product Stories

1. Native iPhone voice controller for Johnny-Johnny.
2. Guided pgvector, LangChain, and LangGraph RAG plus safe tool-execution story.
