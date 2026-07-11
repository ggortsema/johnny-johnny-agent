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
ASSISTANT_SMOKE_TEXT="${ASSISTANT_SMOKE_TEXT:-Confirm that the Johnny-Johnny assistant endpoint is responding.}"

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
ASSISTANT_URL="${PUBLIC_BASE_URL}/api/v1/assistant/responses"

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

print_step "Verify assistant endpoint rejects missing token"
UNAUTHENTICATED_ASSISTANT_STATUS="$(
  curl -sS \
    -o "${HTTP_BODY}" \
    -w '%{http_code}' \
    -X POST \
    -H 'Content-Type: application/json' \
    --data-binary '{"text":"Hello"}' \
    "${ASSISTANT_URL}"
)"

if [[ "${UNAUTHENTICATED_ASSISTANT_STATUS}" != "401" ]]; then
  cat "${HTTP_BODY}" >&2
  echo \
    "Expected unauthenticated assistant status 401, received ${UNAUTHENTICATED_ASSISTANT_STATUS}." \
    >&2
  exit 1
fi

echo "Unauthenticated assistant request correctly returned 401."

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
  echo "Authenticated backlog 200 and authorization 403 smoke tests were skipped."
fi

if [[ -n "${ASSISTANT_ACCESS_TOKEN:-}" ]]; then
  print_step "Verify authenticated assistant response"

  ASSISTANT_REQUEST="${TEMP_DIR}/assistant-request.json"
  ASSISTANT_SMOKE_TEXT="${ASSISTANT_SMOKE_TEXT}" \
  python3 - <<'PY' > "${ASSISTANT_REQUEST}"
import json
import os

print(json.dumps({"text": os.environ["ASSISTANT_SMOKE_TEXT"]}))
PY

  ASSISTANT_STATUS="$(
    curl -sS \
      -o "${HTTP_BODY}" \
      -w '%{http_code}' \
      -X POST \
      -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}" \
      -H 'Content-Type: application/json' \
      --data-binary @"${ASSISTANT_REQUEST}" \
      "${ASSISTANT_URL}"
  )"

  if [[ "${ASSISTANT_STATUS}" != "200" ]]; then
    cat "${HTTP_BODY}" >&2
    echo \
      "Expected authenticated assistant status 200, received ${ASSISTANT_STATUS}." \
      >&2
    exit 1
  fi

  ASSISTANT_RESPONSE_FILE="${HTTP_BODY}" python3 - <<'PY'
import json
import os
from pathlib import Path

body = json.loads(Path(os.environ["ASSISTANT_RESPONSE_FILE"]).read_text())

for field in ("response_id", "text", "model"):
    value = body.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Assistant response field {field!r} is missing or empty.")

usage = body.get("usage")
if not isinstance(usage, dict):
    raise SystemExit("Assistant response usage is missing.")

for field in ("input_tokens", "output_tokens"):
    value = usage.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SystemExit(f"Assistant usage field {field!r} is invalid.")
PY

  echo "Authenticated assistant request correctly returned normalized generated text."
else
  echo
  echo "ASSISTANT_ACCESS_TOKEN is not set."
  echo "Authenticated assistant generation smoke test was skipped."
fi

print_step "Fast loop completed successfully"
echo "Deployed image: ${IMAGE_URI}"
echo "Public URL: ${PUBLIC_BASE_URL}"
