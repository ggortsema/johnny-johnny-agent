# Session Index

**Date:** July 10, 2026  
**Project:** Johnny-Johnny Agent  
**Git Branch:** dev  
**Current Story:** `deploy-johnny-johnny-api-to-eks`  
**Immediate Status:** Manual EKS deployment in progress; pod is running but readiness is failing because `DATABASE_URL` in AWS Secrets Manager was created with the literal text `echo` prefixed to the URL.

## Session Goal

Prove the direct Johnny-Johnny deployment path manually before integrating it into StyxCD:

```text
test
→ build image
→ push to ECR
→ configure AWS-managed secrets
→ configure EKS workload identity
→ deploy to EKS
→ configure ALB/HTTPS/DNS
→ run public and authenticated smoke tests
```

## Completed This Session

### Local container validation

- Built the Docker image successfully.
- Ran the image locally with `.env`.
- Confirmed Uvicorn started on `0.0.0.0:8000`.
- Confirmed the public liveness endpoint returned:
  ```json
  {"service":"johnny-johnny-agent","version":"0.1.0","status":"ok"}
  ```

### EKS cluster validation

- Confirmed EKS cluster `johnny-johnny-dev` exists and is `ACTIVE`.
- Refreshed kubeconfig.
- Confirmed cluster version `1.34`.
- Confirmed worker architecture is `x86_64`, so deployment images must target:
  ```text
  linux/amd64
  ```

### ECR

- Existing repositories:
  ```text
  johnny-johnny/johnny-johnny-ui
  johnny-johnny/johnny-johnny-backend
  ```
- Created:
  ```text
  johnny-johnny/johnny-johnny-agent
  ```
- Repository URI:
  ```text
  359546647832.dkr.ecr.us-east-1.amazonaws.com/johnny-johnny/johnny-johnny-agent
  ```
- Authenticated Docker to ECR.
- Built and pushed:
  ```text
  359546647832.dkr.ecr.us-east-1.amazonaws.com/johnny-johnny/johnny-johnny-agent:0.1.0
  ```
- Verified digest:
  ```text
  sha256:444b226e5db356486e0017b3d863706cd9c372abb0b473ab7e013295d446376a
  ```

### Secrets Manager

Created secrets:

```text
DATABASE_URL
GITHUB_TOKEN
```

Secret ARNs:

```text
arn:aws:secretsmanager:us-east-1:359546647832:secret:DATABASE_URL-kwT9cC
arn:aws:secretsmanager:us-east-1:359546647832:secret:GITHUB_TOKEN-eyDU2F
```

Important current problem:

- `DATABASE_URL` was entered incorrectly with literal `echo` text in front of the URL.
- The running container therefore receives an invalid database connection string.
- The next session must update the existing `DATABASE_URL` secret with the correct value.

Do not paste secret values into chat.

### EKS Pod Identity

- Installed EKS managed add-on:
  ```text
  eks-pod-identity-agent
  ```
- Verified DaemonSet is ready.
- Created IAM policy file:
  ```text
  johnny-johnny-secrets-policy.json
  ```
- Created IAM policy:
  ```text
  arn:aws:iam::359546647832:policy/JohnnyJohnnyRuntimeSecretsRead
  ```
- Policy allows only:
  ```text
  secretsmanager:GetSecretValue
  secretsmanager:DescribeSecret
  ```
  for the two Johnny-Johnny secret ARNs.
- Created Pod Identity trust policy:
  ```text
  johnny-johnny-pod-identity-trust-policy.json
  ```
- Created IAM role:
  ```text
  arn:aws:iam::359546647832:role/JohnnyJohnnyAgentPodIdentityRole
  ```
- Attached `JohnnyJohnnyRuntimeSecretsRead`.
- Created Kubernetes ServiceAccount:
  ```text
  namespace: johnny-johnny
  serviceAccount: johnny-johnny-agent
  ```
- Created EKS Pod Identity association:
  ```text
  association id: a-768ibt7adlppkyfuc
  namespace: johnny-johnny
  service account: johnny-johnny-agent
  role: JohnnyJohnnyAgentPodIdentityRole
  ```

### Secrets Store CSI Driver / AWS provider

- Added Helm repo:
  ```text
  aws-secrets-manager
  ```
- Installed release:
  ```text
  secrets-provider-aws
  ```
  in:
  ```text
  kube-system
  ```
- Initial install failed because the single `t3.small` worker had reached its 11-pod limit.
- Node group:
  ```text
  ng-7996e69b
  ```
- Original scaling:
  ```text
  min=1
  desired=1
  max=1
  ```
- Updated scaling:
  ```text
  min=1
  desired=2
  max=2
  ```
- Second worker joined and became ready.
- Old Johnny-Johnny UI and Java backend Deployments were scaled to zero to free pod slots:
  ```text
  johnny-johnny-ui
  johnny-johnny-backend
  ```
- Helm release eventually reached:
  ```text
  STATUS: deployed
  ```
- Both DaemonSets are healthy on both nodes:
  ```text
  secrets-store-csi-driver
  secrets-provider-aws-secrets-store-csi-driver-provider-aws
  ```

### SecretProviderClass

Created and applied:

```text
johnny-johnny-secret-provider-class.yml
```

Resource:

```text
kind: SecretProviderClass
name: johnny-johnny-agent-secrets
namespace: johnny-johnny
provider: aws
usePodIdentity: "true"
```

It maps:

```text
DATABASE_URL
GITHUB_TOKEN
```

from Secrets Manager to mounted files under:

```text
/mnt/secrets-store
```

### Johnny-Johnny Kubernetes Deployment

Created and applied:

```text
johnny-johnny-agent-deployment.yml
```

Deployment:

```text
name: johnny-johnny-agent
namespace: johnny-johnny
replicas: 1
serviceAccountName: johnny-johnny-agent
image: 359546647832.dkr.ecr.us-east-1.amazonaws.com/johnny-johnny/johnny-johnny-agent:0.1.0
```

The container startup command reads mounted secrets and exports them before starting the API:

```sh
export DATABASE_URL="$(cat /mnt/secrets-store/DATABASE_URL)"
export GITHUB_TOKEN="$(cat /mnt/secrets-store/GITHUB_TOKEN)"
exec jj serve --host 0.0.0.0 --port 8000
```

Non-secret runtime configuration:

```text
AUTH0_DOMAIN=dev-ude3gljkecu7ylzt.us.auth0.com
AUTH0_AUDIENCE=https://johnny-johnny.mycroftai.org
JOHNNY_JOHNNY_API_DOCS_ENABLED=false
AUTH0_CLOCK_SKEW_SECONDS=30
AUTH0_JWKS_TIMEOUT_SECONDS=5
AUTH0_JWKS_CACHE_SECONDS=300
```

Health probes:

```text
readiness: /api/v1/health/ready
liveness:  /api/v1/health/live
```

## Current Runtime State

Pod:

```text
johnny-johnny-agent-575bddfb67-t5bs6
```

State:

```text
STATUS: Running
READY: 0/1
RESTARTS: 0
```

Liveness succeeds:

```text
GET /api/v1/health/live → 200
```

Readiness fails:

```text
GET /api/v1/health/ready → 503
```

Readiness body:

```json
{
  "service": "johnny-johnny-agent",
  "version": "0.1.0",
  "status": "not-ready",
  "checks": {
    "database": "unavailable",
    "canonical_schema": "unknown"
  }
}
```

The mounted secret and process environment were inspected manually. The cause was found:

```text
DATABASE_URL begins with literal "echo"
```

This is why database readiness fails.

## Immediate First Task Next Session

Update the existing `DATABASE_URL` secret safely.

Use a hidden prompt:

```bash
read -s -p "DATABASE_URL: " DATABASE_URL_SECRET
```

Paste only the actual PostgreSQL URL and press Enter.

Then update the existing AWS secret:

```bash
aws secretsmanager put-secret-value   --secret-id DATABASE_URL   --region us-east-1   --secret-string "$DATABASE_URL_SECRET"
```

Then restore terminal echo if needed:

```bash
stty echo
```

Clear the local shell variable:

```bash
unset DATABASE_URL_SECRET
```

Because Secrets Store CSI-mounted files may not refresh immediately and the environment variables are exported only at container startup, restart the Deployment after the secret is corrected:

```bash
kubectl rollout restart deployment/johnny-johnny-agent -n johnny-johnny
```

Poll rather than wait:

```bash
kubectl get pods -n johnny-johnny -l app=johnny-johnny-agent
```

Then poll:

```bash
kubectl get deployment johnny-johnny-agent -n johnny-johnny
```

Expected:

```text
READY 1/1
AVAILABLE 1
```

Then verify readiness from inside the container or through a Service once created.

## Remaining Manual Deployment Work

After database readiness is fixed:

1. Create the Kubernetes `Service` for `johnny-johnny-agent`.
2. Confirm service-to-pod connectivity.
3. Confirm or request ACM certificate for:
   ```text
   johnny-johnny.mycroftai.org
   ```
4. Create ALB Ingress with HTTPS listener and certificate ARN.
5. Configure Route53 alias to the ALB.
6. Validate:
   - public liveness → `200`
   - protected endpoint without token → `401`
   - valid Auth0 read token → `200`
   - insufficient scope → `403`
7. Build a repeatable Bash deployment loop.
8. Stop and create a separate StyxCD integration story.

## StyxCD Design Insight Exposed

Current `EksDeployApplication` handles secrets as:

```text
Jenkins credentials
→ kubectl create secret generic
→ Kubernetes Secret
→ env.secretKeyRef
```

The new AWS-native capability should support:

```text
AWS Secrets Manager
→ IAM policy
→ Pod Identity role
→ EKS Pod Identity association
→ Secrets Store CSI Driver / AWS provider
→ SecretProviderClass
→ mounted runtime secret
```

Recommended future StyxCD split:

```text
Cluster capability stage:
- ensure Pod Identity Agent
- ensure Secrets Store CSI Driver
- ensure AWS provider

Application identity stage:
- IAM policy
- IAM role
- Pod Identity association

Deploy application stage:
- ServiceAccount
- SecretProviderClass
- Deployment
- Service
```

Do not hide all IAM and cluster setup inside `EksDeployApplication`.

## Working Preference Reinforced

Provide exactly one shell command at a time. Do not include follow-on commands until the user returns the result.

The user prefers polling commands over commands that wait indefinitely, such as:

```text
kubectl rollout status
kubectl get ... -w
```

## Files Created Locally During This Session

```text
johnny-johnny-secrets-policy.json
johnny-johnny-pod-identity-trust-policy.json
johnny-johnny-secret-provider-class.yml
johnny-johnny-agent-deployment.yml
```

These should be reviewed and moved into an appropriate deployment directory before commit.

## Important Temporary Infrastructure State

- Node group currently has two `t3.small` workers.
- Old UI and Java backend Deployments are scaled to zero, not deleted.
- The Helm secret-provider release is deployed and healthy.
- The Johnny-Johnny agent Deployment exists but is not ready until `DATABASE_URL` is corrected.
