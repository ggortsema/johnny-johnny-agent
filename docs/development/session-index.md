# Session Index

**Date:** July 10, 2026  
**Project Version:** 0.1.0  
**Git Branch:** dev  
**Completed Story:** `deploy-johnny-johnny-api-to-eks`  
**Current Story:** None; deployment story completed and released  
**Next Story:** `implement-assistant-response-endpoint`  
**Following Story:** Minimal authenticated web UI  
**Deferred Story:** Integrate proven deployment contract into StyxCD

## Session Summary

The Johnny-Johnny Python API was deployed manually to EKS, secured with HTTPS and Auth0 OAuth 2.0, connected successfully to PostgreSQL, and then wrapped in a tested developer fast loop.

The work moved from a running but unready pod to a complete public deployment:

```text
Route 53
→ HTTPS ALB
→ Kubernetes Ingress
→ ClusterIP Service
→ EKS Pod
→ FastAPI
→ PostgreSQL
```

Runtime secrets are delivered through:

```text
AWS Secrets Manager
→ EKS Pod Identity
→ Secrets Store CSI
→ mounted files
→ process environment
```

The deployment automation was committed, merged to `main`, tagged, and development returned to `dev`. The exact tag name was not captured in the session.

## Stories Completed

### Deploy Johnny-Johnny API to EKS

Completed and validated:

- Docker image built for `linux/amd64`.
- Image pushed to ECR.
- EKS Pod Identity Agent installed.
- Secrets Store CSI Driver and AWS provider installed.
- Runtime IAM policy and role created.
- Pod Identity association created.
- `DATABASE_URL` and `GITHUB_TOKEN` projected from AWS Secrets Manager.
- Deployment readiness passed.
- ClusterIP Service created and validated.
- Existing ALB and Ingress reused.
- ACM certificate issued for MycroftAI and StyxCD apex/wildcard names.
- Route 53 DNS validation completed.
- HTTPS listener and HTTP redirect configured.
- public liveness returned `200`.
- protected call without token returned `401`.
- Auth0 M2M token was validated.
- authenticated backlog read returned `200`.
- valid token missing reconciliation authority returned `403`.
- fast-loop automation was created and successfully executed.
- rollout polling race was found and fixed.
- work was committed, merged, tagged, and returned to `dev`.

## Engineering Artifacts Created During the Session

Repository artifacts:

```text
docs/deployment/eks/kubernetes/johnny-johnny-namespace.yml
docs/deployment/eks/kubernetes/johnny-johnny-agent-service-account.yml
docs/deployment/eks/kubernetes/johnny-johnny-agent-service.yml
docs/deployment/eks/kubernetes/johnny-johnny-ingress.yml
scripts/fast-loop.sh
```

Previously created deployment artifacts organized during this session:

```text
docs/deployment/eks/iam/johnny-johnny-pod-identity-trust-policy.json
docs/deployment/eks/iam/johnny-johnny-secrets-policy.json
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
docs/deployment/eks/kubernetes/johnny-johnny-secret-provider-class.yml
```

Session-closure artifacts generated now:

```text
ADR-JOHNNY-JOHNNY-EKS-DEPLOYMENT.md
EKS-DEPLOYMENT-FAST-LOOP.md
ASSISTANT-RESPONSE-ENDPOINT-STORY.md
BACKLOG-UPDATE-2026-07-10.md
command-cheat-sheet-2026-07-10-234606.md
session-index.md
engineering-session-closure-report.md
```

## Engineering Artifacts Updated

- Engineering Session Closure process now requires a timestamped command cheat sheet.
- The deployment manifest set became fully declarative.
- The Service and ServiceAccount exports were cleaned of cluster-generated fields.
- The Ingress now routes the public Johnny-Johnny hostname to the Python API and terminates HTTPS.
- The fast loop now uses a generation-aware, exact-image rollout gate.

## Architectural Decisions

- The Python agent replaces the Java backend as the active backend.
- The old Java and UI Deployments remain scaled to zero for now.
- Reuse the existing ALB and Ingress instead of creating a temporary ALB.
- Until the UI exists, `johnny-johnny.mycroftai.org/` routes to the Python agent.
- When the UI exists, route `/` to the UI and `/api/v1` to the Python agent.
- Use AWS Secrets Manager, EKS Pod Identity, and CSI-mounted secrets rather than Kubernetes Secrets.
- Keep the public Johnny-Johnny API reachable over HTTPS for web, iPhone, and future webhook clients.
- Keep OAuth bearer-token authorization separate from future GitHub webhook HMAC verification.
- Treat the Bash fast loop as an executable deployment contract, not the final platform.
- Defer StyxCD integration into a separate story.
- Before the UI, implement one minimal provider-neutral assistant response endpoint.
- Protect the assistant endpoint with a dedicated `invoke:assistant` scope.
- Keep `OPENAI_API_KEY` server-side and AWS-managed.
- Use a language-model provider port so later RAG work does not require changing the public endpoint.

## Bugs Found and Fixed

### Invalid `DATABASE_URL`

The AWS secret contained the literal text `echo` before the PostgreSQL URL. The secret was safely replaced, the Deployment restarted, and readiness became healthy.

### Rollout false-success race

The first fast-loop poll could potentially pass while an old ready pod still satisfied readiness and the new pod was starting.

The replacement gate now requires:

- expected generation observed;
- old pod removed;
- exact final pod count;
- every pod on the exact new image;
- every pod ready;
- zero unavailable replicas.

### Incorrect project path

An authenticated request using `johnny-johnny` returned `404`. The correct database identity is the URL-encoded provider project title:

```text
Johnny-Johnny Backlog Persistence Sandbox
```

### AWS CLI table query shape

A certificate query mixed a scalar and nested rows, which `--output table` could not render. Separate queries were used.

### Certificate wildcard depth

`*.mycroftai.org` does not cover `api.johnny-johnny.mycroftai.org`. Reusing `johnny-johnny.mycroftai.org` avoided the nested-hostname problem.

## Testing and Validation

- Full Python test suite passed through `uv run pytest` during the fast loop.
- Kubernetes manifest directory passed client-side dry-run validation.
- Internal Service routing returned healthy JSON.
- Public HTTPS liveness and readiness passed.
- Auth0 `whoami` returned the M2M subject and scopes.
- Authenticated PostgreSQL-backed read passed.
- Missing-token and missing-scope boundaries passed.
- Complete fast loop passed after the rollout gate was strengthened.

## Lessons Learned

- A pod can be running while readiness correctly blocks traffic.
- A Kubernetes Service forwards to selected Pod IPs and target ports; it does not redirect HTTP.
- `kubectl get ingress` is not the authoritative source for actual ALB listeners.
- ALB default listener action can be a fixed response while host rules route application traffic.
- ACM may reuse one validation CNAME for an apex/wildcard pair.
- `curl -f` is useful for success-only scripts but hides expected authorization response bodies.
- Bash is excellent for proving an orchestration contract and poor as the long-term extensibility boundary.
- The manually proven script provides concrete StyxCD use cases rather than theoretical requirements.

## Outstanding Work

### Immediate product work

- Implement the assistant-response endpoint.
- Add the OpenAI provider adapter and provider-neutral port.
- Add `invoke:assistant` to Auth0.
- Store `OPENAI_API_KEY` in AWS Secrets Manager.
- Add the new key to the IAM policy and SecretProviderClass.
- Add `OPENAI_MODEL` as non-secret deployment configuration.
- Add tests and deploy with the fast loop.
- Build the minimal web UI.
- Continue toward the native iPhone controller and RAG.

### Deployment cleanup and hardening

- Decide whether to archive or delete `johnny-johnny-ingress-before-agent.yml`.
- Retire the Java backend resources when no longer needed.
- Replace or update the old UI when the new web client is ready.
- Consider adding ShellCheck and behavior tests for `fast-loop.sh`.
- Consider ECR lifecycle policy for timestamped images.
- Consider rollback behavior and failed-rollout diagnostics.
- Confirm the release tag name in project history if needed.
- Review the temporary two-node `t3.small` development posture and cost.

### Deferred platform work

- Convert the proven deployment contract into StyxCD capabilities.
- Keep Forge-specific automation and StyxCD code/configuration legally and technically separate.

## Next Recommended Starting Point

Create or move the `implement-assistant-response-endpoint` backlog item to In Progress.

Then inspect the existing route, authentication, configuration, error-handling, and behavior-test structure before designing code changes.

## Files Likely Needed Next Session

```text
ASSISTANT-RESPONSE-ENDPOINT-STORY.md
BACKLOG-UPDATE-2026-07-10.md
pyproject.toml
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/api/routes.py
existing authentication and authorization modules
existing API error models and handlers
tests/behavior/
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
docs/deployment/eks/kubernetes/johnny-johnny-secret-provider-class.yml
docs/deployment/eks/iam/johnny-johnny-secrets-policy.json
scripts/fast-loop.sh
```

## Immediate First Task

Inspect the implementation files for:

```text
API routing
scope enforcement
dependency construction
configuration loading
error translation
behavior-test conventions
```

Then design the provider-neutral assistant use case and OpenAI adapter before editing code.

## Session Completion State

The EKS deployment story is complete.

The next engineering phase is:

```text
minimal assistant endpoint
→ deploy through fast loop
→ minimal web UI
→ RAG capability
→ native iPhone controller
```
