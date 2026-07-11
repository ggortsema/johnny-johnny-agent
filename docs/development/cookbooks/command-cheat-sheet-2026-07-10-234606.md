# Command Cheat Sheet

**Session:** Johnny-Johnny EKS deployment, HTTPS/OAuth validation, and fast-loop automation  
**Generated:** 2026-07-10T23:46:06.889163-04:00  
**Filename:** `command-cheat-sheet-2026-07-10-234606.md`

## Safety conventions

- Secret values are never included.
- Commands that read secrets use hidden prompts.
- Tokens and secrets remain in shell variables only.
- The failed or superseded commands are retained where they taught an important lesson.

# Bash / Shell

## Read the corrected database URL without terminal echo

```bash
read -s -p "DATABASE_URL: " DATABASE_URL_SECRET
```

Reads the PostgreSQL URL into a shell variable without displaying it.

## Clear the local database URL variable

```bash
unset DATABASE_URL_SECRET
```

Removes the secret value from the current shell after updating AWS Secrets Manager.

## Inspect Auth0 environment-variable names without printing values

```bash
grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env | cut -d= -f1 | grep '^AUTH0_'
```

Lists only Auth0 variable names present in `.env`.

## Search the repository for Auth0 M2M credential conventions

```bash
grep -RInE 'AUTH0_(CLIENT_ID|CLIENT_SECRET)|CLIENT_ID|CLIENT_SECRET' \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude='.env' \
  .
```

Finds documentation and code references without searching the actual `.env` values.

## Show the documented Auth0 token flow

```bash
sed -n '140,190p' README.md
```

Displays the README section for acquiring an Auth0 M2M token.

## Load Auth0 domain and audience from `.env`

```bash
export AUTH0_DOMAIN="$(grep '^AUTH0_DOMAIN=' .env | cut -d= -f2-)" AUTH0_AUDIENCE="$(grep '^AUTH0_AUDIENCE=' .env | cut -d= -f2-)"
```

Exports the deployed Auth0 validation values without printing them.

## Read the M2M Client ID

```bash
read -p "Auth0 M2M client ID: " AUTH0_CLIENT_ID && export AUTH0_CLIENT_ID
```

Reads and exports the Auth0 Client ID. This value is not a secret, so terminal echo is enabled.

## Read the M2M Client Secret without terminal echo

```bash
read -rsp "Auth0 M2M client secret: " AUTH0_CLIENT_SECRET && echo && export AUTH0_CLIENT_SECRET
```

Reads and exports the Auth0 Client Secret without displaying it.

## Build the OAuth token request body

```bash
TOKEN_REQUEST="$(
  python3 - <<'PY'
import json
import os

print(json.dumps({
    "client_id": os.environ["AUTH0_CLIENT_ID"],
    "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
    "audience": os.environ["AUTH0_AUDIENCE"],
    "grant_type": "client_credentials",
}))
PY
)"
```

Creates the Auth0 client-credentials request as JSON without printing the secret.

## Request an Auth0 token

```bash
TOKEN_RESPONSE="$(
  printf '%s' "${TOKEN_REQUEST}" \
    | curl -fsS -X POST \
        "https://${AUTH0_DOMAIN}/oauth/token" \
        -H 'Content-Type: application/json' \
        --data-binary @-
)"
```

Calls the Auth0 token endpoint and keeps the response in a shell variable.

## Extract the access token

```bash
export ACCESS_TOKEN="$(
  printf '%s' "${TOKEN_RESPONSE}" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])'
)"
```

Extracts and exports the bearer token without displaying it.

## Search for backlog route examples

```bash
grep -RInE '/backlogs/.*/items|project_path' README.md docs src \
  --exclude-dir='__pycache__'
```

Finds the documented and implemented backlog path conventions.

## Show the protected-read walkthrough

```bash
sed -n '340,400p' README.md
```

Displays the README curl examples for PostgreSQL-backed reads.

## Show the walkthrough setup variables

```bash
sed -n '300,340p' README.md
```

Displays the provider account and URL-encoded project title used by the smoke tests.

## Inspect the move/reconciliation area of the README

```bash
sed -n '560,610p' README.md
```

Displays the later mutation examples. This first range did not yet include the full reconciliation command.

## Locate the exact reconciliation example

```bash
grep -n -A30 -B5 -i 'reconcile' README.md
```

Finds the complete dry-run reconciliation request.

## Inspect the top-level directory structure

```bash
find . -maxdepth 2 -type d | sort
```

Identifies natural homes for deployment manifests and automation.

## Inspect existing scripts

```bash
find scripts -maxdepth 2 -type f | sort
```

Confirms whether the scripts directory already contains automation.

## Search the project root for deployment files

```bash
find . -maxdepth 1 -type f \( \
  -name '*johnny-johnny*.yml' -o \
  -name '*johnny-johnny*.yaml' -o \
  -name '*johnny-johnny*.json' \
\) | sort
```

Locates Johnny-Johnny deployment files still at repository root.

## Locate Johnny-Johnny deployment files across the repository

```bash
find . -type f \( \
  -name 'johnny-johnny-*.yml' -o \
  -name 'johnny-johnny-*.yaml' -o \
  -name 'johnny-johnny-*.json' \
\) -not -path './.git/*' | sort
```

Shows the complete current deployment-artifact layout.

## Move the active Ingress manifest into the deployment directory

```bash
mv johnny-johnny-ingress.yml docs/deployment/eks/kubernetes/
```

Places the active Ingress manifest with the rest of the EKS resources.

## Inspect the captured Service manifest

```bash
cat docs/deployment/eks/kubernetes/johnny-johnny-agent-service.yml
```

Shows cluster-generated fields that need removal before commit.

## Replace the Service with a clean declarative manifest

```bash
cat > docs/deployment/eks/kubernetes/johnny-johnny-agent-service.yml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: johnny-johnny-agent
  namespace: johnny-johnny
spec:
  type: ClusterIP
  selector:
    app: johnny-johnny-agent
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8000
EOF
```

Defines stable Service intent without cluster-assigned IPs, UIDs, timestamps, or status.

## Inspect the Deployment manifest

```bash
cat docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
```

Reviews image, runtime configuration, probes, and secret mounts before automation.

## Inspect the captured ServiceAccount manifest

```bash
cat docs/deployment/eks/kubernetes/johnny-johnny-agent-service-account.yml
```

Shows cluster-generated metadata that should not be committed.

## Replace the ServiceAccount with a clean manifest

```bash
cat > docs/deployment/eks/kubernetes/johnny-johnny-agent-service-account.yml <<'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: johnny-johnny-agent
  namespace: johnny-johnny
EOF
```

Defines the Pod Identity-associated ServiceAccount. No IRSA annotation is required.

## Create the Namespace manifest

```bash
cat > docs/deployment/eks/kubernetes/johnny-johnny-namespace.yml <<'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: johnny-johnny
EOF
```

Makes the namespace a declarative prerequisite.

## Inspect the Dockerfile

```bash
sed -n '1,220p' Dockerfile
```

Reviews the multi-stage build, frozen dependencies, non-root runtime, and API entry point.

## Inspect project metadata and test configuration

```bash
sed -n '1,180p' pyproject.toml
```

Finds the project version, dependencies, command entry point, and pytest configuration.

## Make the fast-loop script executable

```bash
chmod +x scripts/fast-loop.sh
```

Sets the executable bit, which Git preserves on macOS and Linux.

## Verify the executable-bit change

```bash
git diff --summary scripts/fast-loop.sh
```

Shows the file-mode change Git will record.

## Validate Bash syntax

```bash
bash -n scripts/fast-loop.sh
```

Parses the script without executing deployment actions. No output means the syntax is valid.

## Run the complete developer deployment loop

```bash
./scripts/fast-loop.sh
```

Runs tests, builds and pushes the image, deploys it, waits for the exact new workload, and performs HTTP/OAuth smoke tests.

# AWS CLI

## Replace the existing database secret

```bash
aws secretsmanager put-secret-value \
  --secret-id DATABASE_URL \
  --region us-east-1 \
  --secret-string "$DATABASE_URL_SECRET"
```

Creates a new version of the existing secret using the corrected hidden shell value.

## List existing ACM certificates

```bash
aws acm list-certificates \
  --region us-east-1 \
  --query 'CertificateSummaryList[].[DomainName,Status,CertificateArn]' \
  --output table
```

Checks whether a usable certificate already exists in the ALB region.

## Request one certificate for MycroftAI and StyxCD

```bash
aws acm request-certificate \
  --domain-name mycroftai.org \
  --subject-alternative-names '*.mycroftai.org' styxcd.com '*.styxcd.com' \
  --validation-method DNS \
  --region us-east-1 \
  --query CertificateArn \
  --output text
```

Requests a DNS-validated certificate containing both apex names and both one-level wildcards.

## Retrieve ACM DNS validation records

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:359546647832:certificate/abaebef4-45a5-4f2c-9652-d119353b054c \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[].[DomainName,ResourceRecord.Name,ResourceRecord.Type,ResourceRecord.Value]' \
  --output table
```

Lists the CNAME records required to prove control of each domain.

## Find the Route 53 hosted zones

```bash
aws route53 list-hosted-zones-by-name \
  --query "HostedZones[?Name=='mycroftai.org.' || Name=='styxcd.com.'].[Name,Id,Config.PrivateZone]" \
  --output table
```

Retrieves the public hosted-zone IDs for both domains.

## Create the MycroftAI ACM validation record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z09421751HCBHSEPNDR1D \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "_d355855bbc032270a47ad5759d0c8049.mycroftai.org.",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [
            {
              "Value": "_6bf5479d830a3989a69d5c3695b5ca93.jkddzztszm.acm-validations.aws."
            }
          ]
        }
      }
    ]
  }'
```

Adds or updates the MycroftAI DNS proof record.

## Create the StyxCD ACM validation record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z0033147IBEJCCYGMGKV \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "_cce7208729890bd9bdb4fd404d5b25a2.styxcd.com.",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [
            {
              "Value": "_ad5083c71616b1735c66c2baed6b782c.jkddzztszm.acm-validations.aws."
            }
          ]
        }
      }
    ]
  }'
```

Adds or updates the StyxCD DNS proof record.

## Check overall certificate status

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:359546647832:certificate/abaebef4-45a5-4f2c-9652-d119353b054c \
  --region us-east-1 \
  --query 'Certificate.Status' \
  --output text
```

Polls until ACM reports `ISSUED`.

## Failed mixed-shape table query

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:359546647832:certificate/abaebef4-45a5-4f2c-9652-d119353b054c \
  --region us-east-1 \
  --query 'Certificate.[Status,DomainValidationOptions[].[DomainName,ValidationStatus]]' \
  --output table
```

This failed because the result combined a scalar and nested rows that the table formatter could not represent uniformly. The lesson is to query these shapes separately or use JSON.

## Resolve the existing ALB ARN

```bash
aws elbv2 describe-load-balancers \
  --region us-east-1 \
  --query "LoadBalancers[?DNSName=='k8s-johnnyjo-johnnyjo-31a4af4980-1937427624.us-east-1.elb.amazonaws.com'].[LoadBalancerArn]" \
  --output text
```

Finds the AWS ARN for the ALB already managed by the Ingress.

## Inspect actual ALB listeners

```bash
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:359546647832:loadbalancer/app/k8s-johnnyjo-johnnyjo-31a4af4980/73553e7a709d97ae \
  --region us-east-1 \
  --query 'Listeners[].[Port,Protocol,Certificates[0].CertificateArn,DefaultActions[0].Type]' \
  --output table
```

Confirms HTTPS on 443 with the ACM certificate and HTTP redirect on port 80.

# kubectl

## Restart the Deployment after changing the mounted secret

```bash
kubectl rollout restart deployment/johnny-johnny-agent -n johnny-johnny
```

Creates a new pod so the startup command reads the corrected mounted secret.

## Poll the agent pods

```bash
kubectl get pods -n johnny-johnny -l app=johnny-johnny-agent
```

Checks pod status without using an indefinite watch.

## Inspect the Deployment summary

```bash
kubectl get deployment johnny-johnny-agent -n johnny-johnny
```

Confirms desired, ready, up-to-date, and available replica counts.

## List namespace Services

```bash
kubectl get services -n johnny-johnny
```

Checks which ClusterIP Services already exist before creating a new one.

## Create the initial agent Service imperatively

```bash
kubectl expose deployment johnny-johnny-agent \
  --namespace johnny-johnny \
  --name johnny-johnny-agent \
  --type ClusterIP \
  --port 80 \
  --target-port 8000
```

Creates a cluster-internal Service mapping port 80 to pod port 8000. This was later replaced by a committed manifest.

## Inspect the Service endpoints

```bash
kubectl get endpoints johnny-johnny-agent -n johnny-johnny
```

Confirms that the Service selector resolved to the ready pod. The legacy Endpoints API emitted a deprecation warning; EndpointSlice is preferred.

## Test the Service from inside the cluster

```bash
kubectl exec -n johnny-johnny deployment/johnny-johnny-agent -- python -c "import urllib.request; print(urllib.request.urlopen('http://johnny-johnny-agent/api/v1/health/live').read().decode())"
```

Proves Service DNS and port forwarding reach FastAPI successfully.

## Verify the AWS Load Balancer Controller

```bash
kubectl get deployment aws-load-balancer-controller -n kube-system
```

Confirms both controller replicas are healthy before changing Ingress.

## List all Ingress resources

```bash
kubectl get ingress -A
```

Finds the existing Johnny-Johnny ALB-backed Ingress.

## Inspect the existing Ingress YAML

```bash
kubectl get ingress johnny-johnny-ingress -n johnny-johnny -o yaml
```

Reviews existing UI and Java backend host rules before replacing them.

## Save the pre-agent Ingress

```bash
kubectl get ingress johnny-johnny-ingress \
  -n johnny-johnny \
  -o yaml \
  > johnny-johnny-ingress-before-agent.yml
```

Creates a local rollback/reference copy before changing the active route.

## Create the HTTPS agent-only Ingress manifest

```bash
cat > johnny-johnny-ingress.yml <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: johnny-johnny-ingress
  namespace: johnny-johnny
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:359546647832:certificate/abaebef4-45a5-4f2c-9652-d119353b054c
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-port: traffic-port
    alb.ingress.kubernetes.io/healthcheck-path: /api/v1/health/ready
    alb.ingress.kubernetes.io/success-codes: '200'
spec:
  ingressClassName: alb
  rules:
    - host: johnny-johnny.mycroftai.org
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: johnny-johnny-agent
                port:
                  number: 80
EOF
```

Defines HTTPS termination, HTTP redirect, ALB readiness checks, and routing to the Python agent.

## Apply the Ingress

```bash
kubectl apply -f johnny-johnny-ingress.yml
```

Updates the existing ALB-backed Ingress without creating a second ALB.

## Poll the Ingress summary

```bash
kubectl get ingress johnny-johnny-ingress -n johnny-johnny
```

Confirms the hostname and existing ALB address remain attached.

## Inspect Ingress reconciliation and backend endpoints

```bash
kubectl describe ingress johnny-johnny-ingress -n johnny-johnny
```

Confirms the backend points to the agent Service and the AWS controller reconciled successfully.

## Capture the live Service as YAML

```bash
kubectl get service johnny-johnny-agent \
  -n johnny-johnny \
  -o yaml \
  > docs/deployment/eks/kubernetes/johnny-johnny-agent-service.yml
```

Exports the proven live Service as a starting point for a clean manifest.

## Validate the cleaned Service manifest

```bash
kubectl apply \
  --dry-run=client \
  -f docs/deployment/eks/kubernetes/johnny-johnny-agent-service.yml
```

Checks syntax and client-side object generation without modifying the cluster.

## Capture the live ServiceAccount

```bash
kubectl get serviceaccount johnny-johnny-agent \
  -n johnny-johnny \
  -o yaml \
  > docs/deployment/eks/kubernetes/johnny-johnny-agent-service-account.yml
```

Exports the ServiceAccount before cleaning generated metadata.

## Validate the cleaned ServiceAccount

```bash
kubectl apply \
  --dry-run=client \
  -f docs/deployment/eks/kubernetes/johnny-johnny-agent-service-account.yml
```

Checks the declarative ServiceAccount manifest.

## Validate the Namespace manifest

```bash
kubectl apply \
  --dry-run=client \
  -f docs/deployment/eks/kubernetes/johnny-johnny-namespace.yml
```

Checks the Namespace manifest without changing the cluster.

## Validate the full Kubernetes manifest set

```bash
kubectl apply \
  --dry-run=client \
  -f docs/deployment/eks/kubernetes/
```

Proves all committed application manifests can be parsed and applied together.

# curl / HTTP Smoke Tests

## Test public HTTPS liveness

```bash
curl -i https://johnny-johnny.mycroftai.org/api/v1/health/live
```

Proves the complete public HTTPS path reaches Uvicorn and returns `200`.

## Test a protected endpoint without a token

```bash
curl -i https://johnny-johnny.mycroftai.org/api/v1/backlogs/johnny-johnny/items
```

Proves the deployed OAuth boundary rejects unauthenticated access with `401`.

## Validate the token against `whoami`

```bash
curl -i \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  https://johnny-johnny.mycroftai.org/api/v1/auth/whoami
```

Proves token signature, issuer, audience, subject, and scopes are recognized by the deployed API.

## Authenticated read using an incorrect project identifier

```bash
curl -i \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  https://johnny-johnny.mycroftai.org/api/v1/backlogs/johnny-johnny/items
```

Returned a domain-level `404`, proving authentication succeeded but the provider project identity was wrong.

## Authenticated read using the stored provider project title

```bash
curl -i \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://johnny-johnny.mycroftai.org/api/v1/backlogs/Johnny-Johnny%20Backlog%20Persistence%20Sandbox/items?provider=github&provider_account=ggortsema"
```

Proves an authenticated PostgreSQL-backed read returns `200`.

## Reconciliation dry run with `curl -f`

```bash
curl -fsS -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://johnny-johnny.mycroftai.org/api/v1/backlogs/Johnny-Johnny%20Backlog%20Persistence%20Sandbox/reconciliation?provider=github&provider_account=ggortsema" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | python3 -m json.tool
{
  "mode": "dry-run",
  "max_operations": 100
}
JSON
```

Correctly failed with curl error 56/HTTP `403` because the token lacked reconciliation authority. `-f` hid the response body.

## Inspect the expected `403` response without `-f`

```bash
curl -sS -i -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://johnny-johnny.mycroftai.org/api/v1/backlogs/Johnny-Johnny%20Backlog%20Persistence%20Sandbox/reconciliation?provider=github&provider_account=ggortsema" \
  -H 'Content-Type: application/json' \
  --data-binary '{"mode":"dry-run","max_operations":100}'
```

Shows the structured authorization error while proving valid-token/insufficient-scope behavior.

# Fast-loop script creation

## Initial fast-loop implementation

The initial script established the full workflow but had a rollout-observation race: Deployment-level counts could briefly pass while the old ready pod still existed.

```bash
cat > scripts/fast-loop.sh <<'EOF'
#!/usr/bin/env bash

set -Eeuo pipefail
set +x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

AWS_REGION="${AWS_REGION:-us-east-1}"
EKS_CLUSTER="${EKS_CLUSTER:-johnny-johnny-dev}"
NAMESPACE="${NAMESPACE:-johnny-johnny}"
APP_NAME="${APP_NAME:-johnny-johnny-agent}"
ECR_REPOSITORY="${ECR_REPOSITORY:-johnny-johnny/johnny-johnny-agent}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://johnny-johnny.mycroftai.org}"

PROVIDER="${PROVIDER:-github}"
PROVIDER_ACCOUNT="${PROVIDER_ACCOUNT:-ggortsema}"
PROJECT_TITLE="${PROJECT_TITLE:-Johnny-Johnny Backlog Persistence Sandbox}"

MANIFEST_DIR="${MANIFEST_DIR:-${ROOT_DIR}/docs/deployment/eks/kubernetes}"
EXPECTED_RECONCILE_STATUS="${EXPECTED_RECONCILE_STATUS:-403}"
READINESS_TIMEOUT_SECONDS="${READINESS_TIMEOUT_SECONDS:-180}"
READINESS_POLL_SECONDS="${READINESS_POLL_SECONDS:-5}"

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command is not installed or not on PATH: ${command_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"

  if [[ ! -f "${file_path}" ]]; then
    echo "Required file does not exist: ${file_path}" >&2
    exit 1
  fi
}

print_step() {
  printf '\n==> %s\n' "$1"
}

for command_name in aws curl docker git kubectl python3 uv; do
  require_command "${command_name}"
done

NAMESPACE_MANIFEST="${MANIFEST_DIR}/johnny-johnny-namespace.yml"
SERVICE_ACCOUNT_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-service-account.yml"
SECRET_PROVIDER_MANIFEST="${MANIFEST_DIR}/johnny-johnny-secret-provider-class.yml"
SERVICE_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-service.yml"
INGRESS_MANIFEST="${MANIFEST_DIR}/johnny-johnny-ingress.yml"
DEPLOYMENT_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-deployment.yml"

for manifest in \
  "${NAMESPACE_MANIFEST}" \
  "${SERVICE_ACCOUNT_MANIFEST}" \
  "${SECRET_PROVIDER_MANIFEST}" \
  "${SERVICE_MANIFEST}" \
  "${INGRESS_MANIFEST}" \
  "${DEPLOYMENT_MANIFEST}"
do
  require_file "${manifest}"
done

PROJECT_VERSION="$(
  python3 - <<'PY'
import pathlib
import tomllib

with pathlib.Path("pyproject.toml").open("rb") as stream:
    project = tomllib.load(stream)["project"]

print(project["version"])
PY
)"

GIT_SHA="$(git rev-parse --short=12 HEAD)"
UTC_TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"
IMAGE_TAG="${IMAGE_TAG:-${PROJECT_VERSION}-${GIT_SHA}-${UTC_TIMESTAMP}}"

AWS_ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

PROJECT_PATH="$(
  PROJECT_TITLE="${PROJECT_TITLE}" python3 - <<'PY'
import os
import urllib.parse

print(urllib.parse.quote(os.environ["PROJECT_TITLE"], safe=""))
PY
)"

LOCATION_QUERY="provider=${PROVIDER}&provider_account=${PROVIDER_ACCOUNT}"
BACKLOG_ITEMS_URL="${PUBLIC_BASE_URL}/api/v1/backlogs/${PROJECT_PATH}/items?${LOCATION_QUERY}"
RECONCILIATION_URL="${PUBLIC_BASE_URL}/api/v1/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}"

TEMP_DIR="$(mktemp -d)"
RENDERED_DEPLOYMENT="${TEMP_DIR}/johnny-johnny-agent-deployment.yml"
HTTP_BODY="${TEMP_DIR}/http-response-body.txt"

cleanup() {
  rm -rf "${TEMP_DIR}"
}

trap cleanup EXIT

echo "Johnny-Johnny fast loop"
echo "Image: ${IMAGE_URI}"
echo "Cluster: ${EKS_CLUSTER}"
echo "Region: ${AWS_REGION}"
echo "Namespace: ${NAMESPACE}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Warning: the working tree contains uncommitted changes."
fi

print_step "Run test suite"
uv run pytest

print_step "Refresh EKS kubeconfig"
aws eks update-kubeconfig \
  --name "${EKS_CLUSTER}" \
  --region "${AWS_REGION}" \
  >/dev/null

print_step "Verify ECR repository"
aws ecr describe-repositories \
  --repository-names "${ECR_REPOSITORY}" \
  --region "${AWS_REGION}" \
  >/dev/null

print_step "Authenticate Docker to ECR"
aws ecr get-login-password \
  --region "${AWS_REGION}" \
  | docker login \
      --username AWS \
      --password-stdin "${ECR_REGISTRY}"

print_step "Build and push linux/amd64 image"
docker buildx build \
  --platform linux/amd64 \
  --tag "${IMAGE_URI}" \
  --push \
  .

print_step "Render Deployment with versioned image"
SOURCE_DEPLOYMENT="${DEPLOYMENT_MANIFEST}" \
TARGET_DEPLOYMENT="${RENDERED_DEPLOYMENT}" \
IMAGE_URI="${IMAGE_URI}" \
python3 - <<'PY'
import os
import pathlib

source = pathlib.Path(os.environ["SOURCE_DEPLOYMENT"])
target = pathlib.Path(os.environ["TARGET_DEPLOYMENT"])
image_uri = os.environ["IMAGE_URI"]

lines = source.read_text(encoding="utf-8").splitlines()
rendered = []
replaced = False

for line in lines:
    stripped = line.lstrip()

    if not replaced and stripped.startswith("image:"):
        indentation = line[: len(line) - len(stripped)]
        rendered.append(f"{indentation}image: {image_uri}")
        replaced = True
    else:
        rendered.append(line)

if not replaced:
    raise SystemExit("No container image field was found in the Deployment manifest.")

target.write_text("\n".join(rendered) + "\n", encoding="utf-8")
PY

print_step "Apply Kubernetes resources"
kubectl apply -f "${NAMESPACE_MANIFEST}"
kubectl apply -f "${SERVICE_ACCOUNT_MANIFEST}"
kubectl apply -f "${SECRET_PROVIDER_MANIFEST}"
kubectl apply -f "${SERVICE_MANIFEST}"
kubectl apply -f "${INGRESS_MANIFEST}"
kubectl apply -f "${RENDERED_DEPLOYMENT}"

print_step "Poll Deployment readiness"
deadline=$((SECONDS + READINESS_TIMEOUT_SECONDS))

while true; do
  desired="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.spec.replicas}'
  )"

  updated="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.updatedReplicas}' 2>/dev/null || true
  )"

  ready="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true
  )"

  available="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.availableReplicas}' 2>/dev/null || true
  )"

  updated="${updated:-0}"
  ready="${ready:-0}"
  available="${available:-0}"

  echo "desired=${desired} updated=${updated} ready=${ready} available=${available}"

  if [[ "${updated}" == "${desired}" \
     && "${ready}" == "${desired}" \
     && "${available}" == "${desired}" ]]; then
    break
  fi

  if (( SECONDS >= deadline )); then
    echo "Deployment did not become ready within ${READINESS_TIMEOUT_SECONDS} seconds." >&2
    kubectl get pods -n "${NAMESPACE}" -l "app=${APP_NAME}" >&2
    exit 1
  fi

  sleep "${READINESS_POLL_SECONDS}"
done

DEPLOYED_IMAGE="$(
  kubectl get deployment "${APP_NAME}" \
    -n "${NAMESPACE}" \
    -o jsonpath="{.spec.template.spec.containers[?(@.name=='${APP_NAME}')].image}"
)"

if [[ "${DEPLOYED_IMAGE}" != "${IMAGE_URI}" ]]; then
  echo "Unexpected deployed image: ${DEPLOYED_IMAGE}" >&2
  echo "Expected deployed image: ${IMAGE_URI}" >&2
  exit 1
fi

print_step "Verify public liveness"
LIVE_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${PUBLIC_BASE_URL}/api/v1/health/live"
)"

if [[ "${LIVE_STATUS}" != "200" ]]; then
  cat "${HTTP_BODY}" >&2
  echo "Expected liveness status 200, received ${LIVE_STATUS}." >&2
  exit 1
fi

cat "${HTTP_BODY}"
echo

print_step "Verify public readiness"
READY_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${PUBLIC_BASE_URL}/api/v1/health/ready"
)"

if [[ "${READY_STATUS}" != "200" ]]; then
  cat "${HTTP_BODY}" >&2
  echo "Expected readiness status 200, received ${READY_STATUS}." >&2
  exit 1
fi

cat "${HTTP_BODY}"
echo

print_step "Verify protected endpoint rejects missing token"
UNAUTHENTICATED_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${BACKLOG_ITEMS_URL}"
)"

if [[ "${UNAUTHENTICATED_STATUS}" != "401" ]]; then
  cat "${HTTP_BODY}" >&2
  echo "Expected unauthenticated status 401, received ${UNAUTHENTICATED_STATUS}." >&2
  exit 1
fi

echo "Unauthenticated request correctly returned 401."

if [[ -n "${ACCESS_TOKEN:-}" ]]; then
  print_step "Verify authenticated backlog read"

  AUTHENTICATED_STATUS="$(
    curl -sS \
      -o "${HTTP_BODY}" \
      -w '%{http_code}' \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      "${BACKLOG_ITEMS_URL}"
  )"

  if [[ "${AUTHENTICATED_STATUS}" != "200" ]]; then
    cat "${HTTP_BODY}" >&2
    echo "Expected authenticated read status 200, received ${AUTHENTICATED_STATUS}." >&2
    exit 1
  fi

  echo "Authenticated backlog read correctly returned 200."

  print_step "Verify reconciliation authorization boundary"

  RECONCILIATION_STATUS="$(
    curl -sS \
      -o "${HTTP_BODY}" \
      -w '%{http_code}' \
      -X POST \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      -H 'Content-Type: application/json' \
      --data-binary '{"mode":"dry-run","max_operations":100}' \
      "${RECONCILIATION_URL}"
  )"

  if [[ "${RECONCILIATION_STATUS}" != "${EXPECTED_RECONCILE_STATUS}" ]]; then
    cat "${HTTP_BODY}" >&2
    echo "Expected reconciliation status ${EXPECTED_RECONCILE_STATUS}, received ${RECONCILIATION_STATUS}." >&2
    exit 1
  fi

  echo "Reconciliation request correctly returned ${RECONCILIATION_STATUS}."
else
  echo
  echo "ACCESS_TOKEN is not set."
  echo "Authenticated 200 and authorization 403 smoke tests were skipped."
fi

print_step "Fast loop completed successfully"
echo "Deployed image: ${IMAGE_URI}"
echo "Public URL: ${PUBLIC_BASE_URL}"
EOF
```

## Strengthened generation-aware replacement

The final replacement added expected-generation observation, exact pod count, exact image verification for every pod, per-container readiness, and zero unavailable replicas.

```bash
cat > scripts/fast-loop.sh <<'EOF'
#!/usr/bin/env bash

set -Eeuo pipefail
set +x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

AWS_REGION="${AWS_REGION:-us-east-1}"
EKS_CLUSTER="${EKS_CLUSTER:-johnny-johnny-dev}"
NAMESPACE="${NAMESPACE:-johnny-johnny}"
APP_NAME="${APP_NAME:-johnny-johnny-agent}"
ECR_REPOSITORY="${ECR_REPOSITORY:-johnny-johnny/johnny-johnny-agent}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://johnny-johnny.mycroftai.org}"

PROVIDER="${PROVIDER:-github}"
PROVIDER_ACCOUNT="${PROVIDER_ACCOUNT:-ggortsema}"
PROJECT_TITLE="${PROJECT_TITLE:-Johnny-Johnny Backlog Persistence Sandbox}"

MANIFEST_DIR="${MANIFEST_DIR:-${ROOT_DIR}/docs/deployment/eks/kubernetes}"
EXPECTED_RECONCILE_STATUS="${EXPECTED_RECONCILE_STATUS:-403}"
READINESS_TIMEOUT_SECONDS="${READINESS_TIMEOUT_SECONDS:-180}"
READINESS_POLL_SECONDS="${READINESS_POLL_SECONDS:-5}"

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command is not installed or not on PATH: ${command_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"

  if [[ ! -f "${file_path}" ]]; then
    echo "Required file does not exist: ${file_path}" >&2
    exit 1
  fi
}

print_step() {
  printf '\n==> %s\n' "$1"
}

for command_name in aws curl docker git kubectl python3 uv; do
  require_command "${command_name}"
done

NAMESPACE_MANIFEST="${MANIFEST_DIR}/johnny-johnny-namespace.yml"
SERVICE_ACCOUNT_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-service-account.yml"
SECRET_PROVIDER_MANIFEST="${MANIFEST_DIR}/johnny-johnny-secret-provider-class.yml"
SERVICE_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-service.yml"
INGRESS_MANIFEST="${MANIFEST_DIR}/johnny-johnny-ingress.yml"
DEPLOYMENT_MANIFEST="${MANIFEST_DIR}/johnny-johnny-agent-deployment.yml"

for manifest in \
  "${NAMESPACE_MANIFEST}" \
  "${SERVICE_ACCOUNT_MANIFEST}" \
  "${SECRET_PROVIDER_MANIFEST}" \
  "${SERVICE_MANIFEST}" \
  "${INGRESS_MANIFEST}" \
  "${DEPLOYMENT_MANIFEST}"
do
  require_file "${manifest}"
done

PROJECT_VERSION="$(
  python3 - <<'PY'
import pathlib
import tomllib

with pathlib.Path("pyproject.toml").open("rb") as stream:
    project = tomllib.load(stream)["project"]

print(project["version"])
PY
)"

GIT_SHA="$(git rev-parse --short=12 HEAD)"
UTC_TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"
IMAGE_TAG="${IMAGE_TAG:-${PROJECT_VERSION}-${GIT_SHA}-${UTC_TIMESTAMP}}"

AWS_ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

PROJECT_PATH="$(
  PROJECT_TITLE="${PROJECT_TITLE}" python3 - <<'PY'
import os
import urllib.parse

print(urllib.parse.quote(os.environ["PROJECT_TITLE"], safe=""))
PY
)"

LOCATION_QUERY="provider=${PROVIDER}&provider_account=${PROVIDER_ACCOUNT}"
BACKLOG_ITEMS_URL="${PUBLIC_BASE_URL}/api/v1/backlogs/${PROJECT_PATH}/items?${LOCATION_QUERY}"
RECONCILIATION_URL="${PUBLIC_BASE_URL}/api/v1/backlogs/${PROJECT_PATH}/reconciliation?${LOCATION_QUERY}"

TEMP_DIR="$(mktemp -d)"
RENDERED_DEPLOYMENT="${TEMP_DIR}/johnny-johnny-agent-deployment.yml"
HTTP_BODY="${TEMP_DIR}/http-response-body.txt"

cleanup() {
  rm -rf "${TEMP_DIR}"
}

trap cleanup EXIT

echo "Johnny-Johnny fast loop"
echo "Image: ${IMAGE_URI}"
echo "Cluster: ${EKS_CLUSTER}"
echo "Region: ${AWS_REGION}"
echo "Namespace: ${NAMESPACE}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Warning: the working tree contains uncommitted changes."
fi

print_step "Run test suite"
uv run pytest

print_step "Refresh EKS kubeconfig"
aws eks update-kubeconfig \
  --name "${EKS_CLUSTER}" \
  --region "${AWS_REGION}" \
  >/dev/null

print_step "Verify ECR repository"
aws ecr describe-repositories \
  --repository-names "${ECR_REPOSITORY}" \
  --region "${AWS_REGION}" \
  >/dev/null

print_step "Authenticate Docker to ECR"
aws ecr get-login-password \
  --region "${AWS_REGION}" \
  | docker login \
      --username AWS \
      --password-stdin "${ECR_REGISTRY}"

print_step "Build and push linux/amd64 image"
docker buildx build \
  --platform linux/amd64 \
  --tag "${IMAGE_URI}" \
  --push \
  .

print_step "Render Deployment with versioned image"
SOURCE_DEPLOYMENT="${DEPLOYMENT_MANIFEST}" \
TARGET_DEPLOYMENT="${RENDERED_DEPLOYMENT}" \
IMAGE_URI="${IMAGE_URI}" \
python3 - <<'PY'
import os
import pathlib

source = pathlib.Path(os.environ["SOURCE_DEPLOYMENT"])
target = pathlib.Path(os.environ["TARGET_DEPLOYMENT"])
image_uri = os.environ["IMAGE_URI"]

lines = source.read_text(encoding="utf-8").splitlines()
rendered = []
replaced = False

for line in lines:
    stripped = line.lstrip()

    if not replaced and stripped.startswith("image:"):
        indentation = line[: len(line) - len(stripped)]
        rendered.append(f"{indentation}image: {image_uri}")
        replaced = True
    else:
        rendered.append(line)

if not replaced:
    raise SystemExit(
        "No container image field was found in the Deployment manifest."
    )

target.write_text(
    "\n".join(rendered) + "\n",
    encoding="utf-8",
)
PY

print_step "Apply Kubernetes resources"
kubectl apply -f "${NAMESPACE_MANIFEST}"
kubectl apply -f "${SERVICE_ACCOUNT_MANIFEST}"
kubectl apply -f "${SECRET_PROVIDER_MANIFEST}"
kubectl apply -f "${SERVICE_MANIFEST}"
kubectl apply -f "${INGRESS_MANIFEST}"
kubectl apply -f "${RENDERED_DEPLOYMENT}"

EXPECTED_GENERATION="$(
  kubectl get deployment "${APP_NAME}" \
    -n "${NAMESPACE}" \
    -o jsonpath='{.metadata.generation}'
)"

print_step "Poll new Deployment generation until fully ready"
echo "Expected generation: ${EXPECTED_GENERATION}"

deadline=$((SECONDS + READINESS_TIMEOUT_SECONDS))

while true; do
  current_generation="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.metadata.generation}'
  )"

  observed_generation="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.observedGeneration}' 2>/dev/null || true
  )"

  desired="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.spec.replicas}'
  )"

  total="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.replicas}' 2>/dev/null || true
  )"

  updated="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.updatedReplicas}' 2>/dev/null || true
  )"

  ready="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true
  )"

  available="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.availableReplicas}' 2>/dev/null || true
  )"

  unavailable="$(
    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o jsonpath='{.status.unavailableReplicas}' 2>/dev/null || true
  )"

  pod_state="$(
    EXPECTED_IMAGE="${IMAGE_URI}" \
    APP_NAME="${APP_NAME}" \
    kubectl get pods \
      -n "${NAMESPACE}" \
      -l "app=${APP_NAME}" \
      -o json \
    | EXPECTED_IMAGE="${IMAGE_URI}" APP_NAME="${APP_NAME}" python3 -c '
import json
import os
import sys

data = json.load(sys.stdin)
expected_image = os.environ["EXPECTED_IMAGE"]
app_name = os.environ["APP_NAME"]

pod_count = len(data.get("items", []))
expected_image_count = 0
ready_count = 0

for pod in data.get("items", []):
    containers = {
        container["name"]: container
        for container in pod["spec"].get("containers", [])
    }
    statuses = {
        status["name"]: status
        for status in pod.get("status", {}).get("containerStatuses", [])
    }

    container = containers.get(app_name)
    status = statuses.get(app_name)

    if container and container.get("image") == expected_image:
        expected_image_count += 1

    if status and status.get("ready") is True:
        ready_count += 1

print(pod_count, expected_image_count, ready_count)
'
  )"

  IFS=' ' read -r pod_count expected_image_pods ready_pods <<POD_STATE
${pod_state}
POD_STATE

  observed_generation="${observed_generation:-0}"
  desired="${desired:-0}"
  total="${total:-0}"
  updated="${updated:-0}"
  ready="${ready:-0}"
  available="${available:-0}"
  unavailable="${unavailable:-0}"
  pod_count="${pod_count:-0}"
  expected_image_pods="${expected_image_pods:-0}"
  ready_pods="${ready_pods:-0}"

  echo \
    "generation=${current_generation}/${EXPECTED_GENERATION}" \
    "observed=${observed_generation}" \
    "desired=${desired}" \
    "total=${total}" \
    "updated=${updated}" \
    "ready=${ready}" \
    "available=${available}" \
    "unavailable=${unavailable}" \
    "pods=${pod_count}" \
    "expected-image-pods=${expected_image_pods}" \
    "ready-pods=${ready_pods}"

  if [[ "${current_generation}" != "${EXPECTED_GENERATION}" ]]; then
    echo "Deployment generation changed during the fast loop." >&2
    echo \
      "Expected generation ${EXPECTED_GENERATION}, found ${current_generation}." \
      >&2
    exit 1
  fi

  if (( observed_generation >= EXPECTED_GENERATION )) \
    && [[ "${total}" == "${desired}" ]] \
    && [[ "${updated}" == "${desired}" ]] \
    && [[ "${ready}" == "${desired}" ]] \
    && [[ "${available}" == "${desired}" ]] \
    && [[ "${unavailable}" == "0" ]] \
    && [[ "${pod_count}" == "${desired}" ]] \
    && [[ "${expected_image_pods}" == "${desired}" ]] \
    && [[ "${ready_pods}" == "${desired}" ]]; then
    break
  fi

  if (( SECONDS >= deadline )); then
    echo \
      "Deployment did not become fully ready within ${READINESS_TIMEOUT_SECONDS} seconds." \
      >&2

    kubectl get deployment "${APP_NAME}" \
      -n "${NAMESPACE}" \
      -o wide \
      >&2

    kubectl get pods \
      -n "${NAMESPACE}" \
      -l "app=${APP_NAME}" \
      -o wide \
      >&2

    exit 1
  fi

  sleep "${READINESS_POLL_SECONDS}"
done

DEPLOYED_IMAGE="$(
  kubectl get deployment "${APP_NAME}" \
    -n "${NAMESPACE}" \
    -o jsonpath="{.spec.template.spec.containers[?(@.name=='${APP_NAME}')].image}"
)"

if [[ "${DEPLOYED_IMAGE}" != "${IMAGE_URI}" ]]; then
  echo "Unexpected deployed image: ${DEPLOYED_IMAGE}" >&2
  echo "Expected deployed image: ${IMAGE_URI}" >&2
  exit 1
fi

print_step "Verify public liveness"
LIVE_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${PUBLIC_BASE_URL}/api/v1/health/live"
)"

if [[ "${LIVE_STATUS}" != "200" ]]; then
  cat "${HTTP_BODY}" >&2
  echo "Expected liveness status 200, received ${LIVE_STATUS}." >&2
  exit 1
fi

cat "${HTTP_BODY}"
echo

print_step "Verify public readiness"
READY_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${PUBLIC_BASE_URL}/api/v1/health/ready"
)"

if [[ "${READY_STATUS}" != "200" ]]; then
  cat "${HTTP_BODY}" >&2
  echo "Expected readiness status 200, received ${READY_STATUS}." >&2
  exit 1
fi

cat "${HTTP_BODY}"
echo

print_step "Verify protected endpoint rejects missing token"
UNAUTHENTICATED_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    "${BACKLOG_ITEMS_URL}"
)"

if [[ "${UNAUTHENTICATED_STATUS}" != "401" ]]; then
  cat "${HTTP_BODY}" >&2
  echo \
    "Expected unauthenticated status 401, received ${UNAUTHENTICATED_STATUS}." \
    >&2
  exit 1
fi

echo "Unauthenticated request correctly returned 401."

if [[ -n "${ACCESS_TOKEN:-}" ]]; then
  print_step "Verify authenticated backlog read"

  AUTHENTICATED_STATUS="$(
    curl -sS \
      -o "${HTTP_BODY}" \
      -w '%{http_code}' \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      "${BACKLOG_ITEMS_URL}"
  )"

  if [[ "${AUTHENTICATED_STATUS}" != "200" ]]; then
    cat "${HTTP_BODY}" >&2
    echo \
      "Expected authenticated read status 200, received ${AUTHENTICATED_STATUS}." \
      >&2
    exit 1
  fi

  echo "Authenticated backlog read correctly returned 200."

  print_step "Verify reconciliation authorization boundary"

  RECONCILIATION_STATUS="$(
    curl -sS \
      -o "${HTTP_BODY}" \
      -w '%{http_code}' \
      -X POST \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      -H 'Content-Type: application/json' \
      --data-binary '{"mode":"dry-run","max_operations":100}' \
      "${RECONCILIATION_URL}"
  )"

  if [[ "${RECONCILIATION_STATUS}" != "${EXPECTED_RECONCILE_STATUS}" ]]; then
    cat "${HTTP_BODY}" >&2
    echo \
      "Expected reconciliation status ${EXPECTED_RECONCILE_STATUS}, received ${RECONCILIATION_STATUS}." \
      >&2
    exit 1
  fi

  echo \
    "Reconciliation request correctly returned ${RECONCILIATION_STATUS}."
else
  echo
  echo "ACCESS_TOKEN is not set."
  echo "Authenticated 200 and authorization 403 smoke tests were skipped."
fi

print_step "Fast loop completed successfully"
echo "Deployed image: ${IMAGE_URI}"
echo "Public URL: ${PUBLIC_BASE_URL}"
EOF
```

This was the canonical final replacement. It was syntax-checked and executed successfully.

# Git

The user completed the following Git lifecycle after the script passed:

```text
commit changes
merge to main
create release tag
return to dev
```

The exact commands and tag name were not present in the captured session, so they are not reconstructed here.

# Helm

No new Helm commands were run in this session.

The Secrets Store CSI Driver and AWS provider Helm release had already been installed and validated before this continuation.

# PostgreSQL / psql

No direct PostgreSQL or `psql` commands were run in this session.

Database behavior was validated through the readiness endpoint and a protected PostgreSQL-backed API read.

# Key reusable patterns

## Hidden secret update

```text
read secret without echo
→ update managed secret
→ unset shell variable
→ restart workload
→ poll readiness
```

## Safe Kubernetes export-to-manifest workflow

```text
kubectl get resource -o yaml
→ save locally
→ remove cluster-generated identity/status fields
→ client-side dry run
→ commit declarative intent
```

## Deployment completion workflow

```text
capture expected generation
→ wait for observed generation
→ require exact final replica count
→ require exact image on every pod
→ require every pod ready
→ require zero unavailable replicas
→ run external smoke tests
```

## OAuth boundary validation

```text
no token       → 401
valid read     → 200
missing scope  → 403
```
