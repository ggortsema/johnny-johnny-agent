# Johnny-Johnny Command Cheat Sheet

**Session:** Assistant endpoint integration, deployment, and acceptance  
**Timestamp:** July 11, 2026 03:06:55 America/New_York

Sensitive values are never included. Tokens and keys are represented through environment variables, prompts, files, or placeholders.

## Bash / File Synchronization

### Inspect the canonical repository state

```bash
cd johnny-johnny-agent && git status --short --branch
```

Checked that the real repository was on `dev` and clean before copying generated work.

The user ran the equivalent expanded check:

```bash
git status
```

### Preview a mirrored copy with deletion enabled

```bash
cd .. && rsync -avnc --delete   --exclude='.git/'   --exclude='.venv/'   --exclude='__pycache__/'   --exclude='.pytest_cache/'   --exclude='.DS_Store'   johnny-johnny-agent-2/ johnny-johnny-agent/
```

**Dry run only. Do not run without `-n` in this situation.** It revealed that `.env` and `build/` would be deleted.

### Preview only changed or new content without deletion

```bash
rsync -ainc   --exclude='.git/'   --exclude='.venv/'   --exclude='__pycache__/'   --exclude='.pytest_cache/'   --exclude='.DS_Store'   --exclude='.env'   --exclude='build/'   johnny-johnny-agent-2/ johnny-johnny-agent/
```

Itemized the meaningful additions and content changes while preserving local runtime files and test reports.

### Copy the implementation into the canonical repository

```bash
rsync -avc   --exclude='.git/'   --exclude='.venv/'   --exclude='__pycache__/'   --exclude='.pytest_cache/'   --exclude='.DS_Store'   --exclude='.env'   --exclude='build/'   johnny-johnny-agent-2/ johnny-johnny-agent/
```

Copied the generated implementation without replacing Git history, `.env`, or generated test reports.

### Inspect the committed IAM policy document

```bash
cat docs/deployment/eks/iam/johnny-johnny-secrets-policy.json
```

Confirmed that the repository policy included the `OPENAI_API_KEY-*` Secrets Manager ARN pattern.

### Run the executable deployment contract

```bash
./scripts/fast-loop.sh
```

Ran tests, built and pushed the image, applied manifests, waited for the exact rollout, and exercised public smoke tests.

## Git

### Show copied changes

```bash
cd johnny-johnny-agent && git status --short
```

Displayed modified and newly added files after synchronization.

### Optional feature-branch command that was not used

```bash
cd johnny-johnny-agent && git switch -c feature/assistant-response-endpoint
```

**Not run.** The user intentionally copied and committed directly on the already tagged `dev` branch.

### Check whitespace and conflict-marker problems

```bash
git diff --check
```

No output indicated success.

### Review the tracked-file change size

```bash
git diff --stat
```

Summarized line additions and removals before staging.

### Stage all implementation changes

```bash
git add -A
```

Staged tracked and untracked assistant endpoint files.

### Review staged/working-tree state

```bash
git status --short
```

Verified the set of files prepared for commit.

### Commit the tested endpoint

```bash
git add -A && git commit -m "Implement assistant response endpoint"
```

Committed the completed repository implementation on `dev`.

### Push the completed development branch

```bash
git push origin dev
```

Publishes the committed assistant endpoint work to the remote `dev` branch. Confirm remote presence if not already verified.

## Python / uv

### Run the full Python test suite

```bash
uv run pytest
```

Validated the complete canonical repository. Final result: `138 passed`.

### Validate the local OpenAI key file format without printing it

```bash
python3 - <<'PY'
from pathlib import Path

path = Path("../johnny-johnny-openai-key.txt")
value = path.read_text().strip()

if not value:
    raise SystemExit("ERROR: key file is empty")
if value.startswith("OPENAI_API_KEY="):
    raise SystemExit("ERROR: file contains OPENAI_API_KEY= instead of only the raw key")
if value.startswith("echo ") or value.startswith("export "):
    raise SystemExit("ERROR: file contains a shell command instead of only the raw key")
if not value.startswith("sk-"):
    raise SystemExit("ERROR: value does not look like an OpenAI API key")

print("OpenAI key file format looks valid.")
PY
```

Verified syntax only. The file was **not** treated as authoritative and did not overwrite the known-working AWS secret.

## AWS CLI — Secrets Manager

### Check whether the OpenAI secret already exists

```bash
aws secretsmanager describe-secret   --secret-id OPENAI_API_KEY   --region us-east-1   --query '{Name:Name,ARN:ARN}'   --output table
```

Confirmed that `OPENAI_API_KEY` already existed.

### Proposed secret update that was intentionally not run

```bash
aws secretsmanager put-secret-value   --secret-id OPENAI_API_KEY   --secret-string file://../johnny-johnny-openai-key.txt   --region us-east-1   --query '{ARN:ARN,VersionId:VersionId,VersionStages:VersionStages}'   --output table
```

**Not run.** The existing AWS value was already known to work and remained the runtime source of truth.

## AWS CLI — EKS Pod Identity

### List matching pod identity associations

```bash
aws eks list-pod-identity-associations   --cluster-name johnny-johnny-dev   --region us-east-1   --namespace johnny-johnny   --service-account johnny-johnny-agent   --query 'associations[].{AssociationId:associationId,RoleArn:roleArn}'   --output table
```

Returned the association ID. The selected list response did not expose the role ARN.

### Describe the specific pod identity association

```bash
aws eks describe-pod-identity-association   --cluster-name johnny-johnny-dev   --association-id a-768ibt7adlppkyfuc   --region us-east-1   --query 'association.{Namespace:namespace,ServiceAccount:serviceAccount,RoleArn:roleArn}'   --output table
```

Resolved the pod identity role as `JohnnyJohnnyAgentPodIdentityRole`.

## AWS CLI — IAM

### List managed policies attached to the pod identity role

```bash
aws iam list-attached-role-policies   --role-name JohnnyJohnnyAgentPodIdentityRole   --query 'AttachedPolicies[].{PolicyName:PolicyName,PolicyArn:PolicyArn}'   --output table
```

Identified `JohnnyJohnnyRuntimeSecretsRead`.

### Inspect the active managed-policy document

```bash
POLICY_ARN="arn:aws:iam::359546647832:policy/JohnnyJohnnyRuntimeSecretsRead"
VERSION_ID="$(aws iam get-policy   --policy-arn "$POLICY_ARN"   --query 'Policy.DefaultVersionId'   --output text)"

aws iam get-policy-version   --policy-arn "$POLICY_ARN"   --version-id "$VERSION_ID"   --query 'PolicyVersion.Document'   --output json
```

Confirmed that the active policy initially included only `DATABASE_URL` and `GITHUB_TOKEN`.

### List policy versions before creating another

```bash
aws iam list-policy-versions   --policy-arn arn:aws:iam::359546647832:policy/JohnnyJohnnyRuntimeSecretsRead   --query 'Versions[].{VersionId:VersionId,IsDefault:IsDefaultVersion,Created:CreateDate}'   --output table
```

Showed one existing version, so no old-version cleanup was needed.

### Create and activate policy version v2

```bash
aws iam create-policy-version   --policy-arn arn:aws:iam::359546647832:policy/JohnnyJohnnyRuntimeSecretsRead   --policy-document file://docs/deployment/eks/iam/johnny-johnny-secrets-policy.json   --set-as-default   --query 'PolicyVersion.{VersionId:VersionId,IsDefault:IsDefaultVersion,Created:CreateDate}'   --output table
```

Made the repository policy the default and added runtime read access for the OpenAI secret.

## Auth0 Token Handling

### Read a short-lived token without echoing it or placing it in shell history

```bash
read -rsp "Paste the new Auth0 access token: " ASSISTANT_ACCESS_TOKEN; echo; export ASSISTANT_ACCESS_TOKEN
```

Stored the fresh token in the current shell. No token value was printed or written to this cheat sheet.

## HTTP / curl

### Verify the token's current scopes

```bash
curl --silent --show-error --fail-with-body   -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}"   https://johnny-johnny.mycroftai.org/api/v1/auth/whoami   | python3 -m json.tool
```

Confirmed `invoke:assistant`, `read:backlogs`, and `write:backlogs`.

### Exercise the deployed assistant endpoint

```bash
curl --silent --show-error --fail-with-body   -X POST   https://johnny-johnny.mycroftai.org/api/v1/assistant/responses   -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}"   -H "Content-Type: application/json"   -d '{
    "text": "Reply with one sentence confirming that the Johnny-Johnny assistant endpoint is working."
  }'   | python3 -m json.tool
```

Returned a successful normalized response from `gpt-5.6-sol` with generated text and token usage.
