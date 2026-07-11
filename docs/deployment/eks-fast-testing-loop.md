# EKS Fast Testing Loop

**Status:** Design contract for the next story  
**Next story:** `deploy-johnny-johnny-api-to-eks`  
**Date:** July 10, 2026

## Purpose

Define the deployment boundary and the behavior of the Bash build/deploy loop that will be implemented after Auth0 security. This prevents the next phase from embedding local assumptions or secrets into an ad hoc script.

## Target Runtime

The container starts the API with:

```bash
uv run jj serve --host 0.0.0.0 --port 8000
```

Expected request path:

```text
client
  -> public HTTPS hostname
  -> AWS load balancer / ingress
  -> ClusterIP Service
  -> Johnny-Johnny pod :8000
  -> Auth0 token validation
  -> PostgreSQL / GitHub workflows
```

`0.0.0.0` is required for pod-network reachability. It is not a security control.

## Required Decisions Before Implementation

Record concrete values or choices for:

- AWS account and region
- existing or new EKS cluster name
- Kubernetes namespace
- ECR repository name
- public DNS name
- certificate source and ingress controller
- canonical PostgreSQL private endpoint and network path
- secret delivery mechanism, preferably AWS Secrets Manager or SSM with an approved Kubernetes integration
- workload IAM role and service account
- deployment manifest strategy: plain manifests, Kustomize, or Helm
- initial replica count and resource requests/limits
- whether OpenAPI/Swagger is exposed in the deployed environment

The build/deploy script should consume these decisions, not create hidden defaults for them.

## Expected Deployment Artifacts

The EKS story should add and validate:

```text
Dockerfile
.dockerignore
deploy/kubernetes/...
scripts/build-deploy-eks.sh
```

The exact manifest layout depends on the selected packaging strategy, but it must contain:

- Namespace or documented namespace prerequisite
- ServiceAccount and workload identity configuration
- Deployment
- ClusterIP Service
- HTTPS ingress or Gateway resource
- ConfigMap or explicit non-secret environment configuration
- references to externally managed Secrets
- liveness and readiness probes
- resource requests and limits
- rollout and rollback metadata

## Application Configuration in EKS

Non-secret configuration:

```text
AUTH0_DOMAIN
AUTH0_AUDIENCE
OPENAI_MODEL
JOHNNY_JOHNNY_PROVIDER_ACCOUNT
JOHNNY_JOHNNY_API_DOCS_ENABLED
AUTH0_CLOCK_SKEW_SECONDS
AUTH0_JWKS_TIMEOUT_SECONDS
AUTH0_JWKS_CACHE_SECONDS
```

Server secrets:

```text
DATABASE_URL
GITHUB_TOKEN
OPENAI_API_KEY
```

Caller secrets that must **not** be mounted into the API pod:

```text
Auth0 M2M client secret
interactive client credentials
smoke-test bearer token
```

The API validates tokens using public JWKS data and needs no Auth0 client secret.

## Probe Contract

Kubernetes probes use:

```text
liveness:  GET /api/v1/health/live
readiness: GET /api/v1/health/ready
```

Neither route requires a bearer token. Both responses are minimal. Readiness returns `503` until PostgreSQL and the canonical schema are ready.

Suggested initial behavior, to tune with real startup measurements:

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: http
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: http
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

A startup probe may be added if image startup or database availability makes liveness timing brittle. Values are provisional until measured in EKS.

## Bash Script Contract

The first fast-loop script should be deterministic, fail fast, and be safe to rerun.

Suggested invocation:

```bash
AWS_REGION=us-east-1 \
EKS_CLUSTER_NAME=johnny-johnny-dev \
ECR_REPOSITORY=johnny-johnny-agent \
K8S_NAMESPACE=johnny-johnny \
PUBLIC_BASE_URL=https://api.example.com \
./scripts/build-deploy-eks.sh
```

Suggested optional flags:

```text
--skip-build       reuse an existing image tag
--image-tag TAG    override the default immutable tag
--skip-smoke       deploy and stop after rollout
--show-diff        display manifest diff before apply
--rollback-on-fail restore the previous ReplicaSet when rollout/smoke fails
```

### Required steps

1. Enable strict Bash behavior:

   ```bash
   set -Eeuo pipefail
   ```

2. Verify required tools and authenticated contexts:

   ```text
   aws
   docker
   kubectl
   curl
   python3 or jq
   ```

3. Confirm the AWS account, region, cluster, namespace, and kubectl context before mutating anything.
4. Derive an immutable image tag, preferably the Git commit SHA plus a dirty marker prohibition.
5. Authenticate Docker to ECR.
6. Build the image with reproducible inputs and no secret build arguments.
7. Push the immutable image tag.
8. Render or update manifests with the exact image digest or immutable tag.
9. Show `kubectl diff` when practical.
10. Apply the deployment resources.
11. Wait for `kubectl rollout status` with a bounded timeout.
12. Verify public liveness and readiness over HTTPS.
13. Obtain a smoke-test access token from Auth0 outside the pod.
14. Call `/api/v1/auth/whoami` with the bearer token.
15. Optionally call one configured read-only backlog endpoint with `read:backlogs`.
16. Call `POST /api/v1/assistant/responses` with a separate short-lived token granting `invoke:assistant` and validate the normalized response shape.
17. On failure, print deployment events, pod status, recent logs, ingress status, and the prior image reference.
18. Emit the deployed image digest, public URL, rollout revision, and smoke-test result.

## Smoke Authentication

The deployment script must not accept a long-lived bearer token in a committed file or command-line flag. Preferred local behavior:

- read the M2M client secret silently from the terminal, or
- read it from a developer-only environment variable already supplied by the shell/credential tool
- exchange it for a short-lived access token
- immediately unset the secret and token variables on exit through a trap
- keep shell tracing disabled while secrets exist

The first authenticated check should be:

```text
GET /api/v1/auth/whoami
```

This separates Auth0, ingress, and application verification from database diagnostics. A second read-only summary call can then verify PostgreSQL and route scope together. A third assistant call should use a separate `ASSISTANT_ACCESS_TOKEN` with `invoke:assistant`; that token remains outside the pod and is unset after the smoke test.

## Fast-Loop Safety Rules

- Never tag only `latest`; use an immutable tag or digest.
- Never bake `.env`, cloud credentials, database URLs, GitHub tokens, or Auth0 client secrets into the image.
- Never place a client secret or bearer token in Kubernetes pod configuration.
- Never enable `set -x` around token or secret handling.
- Never bypass TLS verification in the successful path.
- Never silently deploy to the current kubectl context without checking the expected cluster.
- Never report success before rollout and authenticated smoke tests pass.
- Keep purge, import, and full reconciliation out of the default deployment smoke path.

## Failure Diagnostics

On a failed rollout or smoke test, collect at minimum:

```bash
kubectl -n "$K8S_NAMESPACE" get deploy,rs,pods,svc,ingress -o wide
kubectl -n "$K8S_NAMESPACE" describe deployment johnny-johnny-agent
kubectl -n "$K8S_NAMESPACE" get events --sort-by=.lastTimestamp
kubectl -n "$K8S_NAMESPACE" logs deployment/johnny-johnny-agent --tail=200
```

Do not print environment variables or full Secret objects. Error output should identify whether failure occurred during build, push, scheduling, startup, readiness, ingress/TLS, Auth0 token exchange, token validation, or database-backed smoke testing.

## Definition of Done for the EKS Story

- A clean checkout can build the image from the locked dependencies.
- The image runs as a non-root user where feasible.
- The pod starts on `0.0.0.0:8000`.
- Liveness and readiness drive Kubernetes state correctly.
- HTTPS is valid at the public hostname.
- A request without a token receives `401` on `/auth/whoami`.
- A valid Auth0 M2M token succeeds on `/auth/whoami`.
- A read-only token succeeds on one configured backlog read.
- A token without the needed scope receives `403`.
- Secrets are supplied through the approved external mechanism.
- The Bash loop builds, pushes, deploys, waits, tests, and produces actionable diagnostics.
- The deployment can be rolled back to the prior image.
