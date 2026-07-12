# Command Cheat Sheet — July 12, 2026

**Generated:** July 12, 2026 at 02:12:36 America/New_York  
**Session:** Johnny-Johnny authenticated web workspace integration and EKS deployment

Secret values, tokens, private keys, and passwords are omitted or replaced with placeholders.

## Bash / Shell

### Enter the canonical UI repository

```bash
cd ~/dev/ai-ecosystem/johnny-johnny/johnny-johnny-ui && git status --short --branch
```

Confirmed the canonical UI repository branch and working-tree state.

### Check for nested Git metadata in the generated UI tree

```bash
find ../johnny-johnny-ui-new -maxdepth 2 -name .git -print
```

Verified that the generated UI source tree did not contain an embedded Git repository.

### Preview full UI replacement

```bash
rsync -avhn --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  ../johnny-johnny-ui-new/ ./
```

Dry-ran the generated UI tree into the canonical UI repository while protecting Git metadata and local environment files.

### Apply full UI replacement

```bash
rsync -avh --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  ../johnny-johnny-ui-new/ ./
```

Copied the new UI source into the canonical repository and intentionally deleted obsolete tracked UI files.

### Inspect active npm process

```bash
ps aux | grep '[n]pm ci'
```

Checked whether the initially silent npm clean install was still running.

### Inspect npm elapsed time and child processes

```bash
ps -o pid,etime,state,%cpu,command -p <NPM_PID>; pgrep -P <NPM_PID> -fl .
```

Helped determine that npm was stalled on registry activity rather than actively installing.

### Check `node_modules` size

```bash
du -sh node_modules 2>/dev/null
```

Provided a simple way to see whether dependency installation was progressing.

### Replace the copied deployment script

```bash
cp ~/Downloads/deploy-eks.sh scripts/deploy-eks.sh
chmod +x scripts/deploy-eks.sh
```

Copied the updated UI deployment script into place and made it executable.

### Verify Auth0 assignments in the script

```bash
grep -n '^AUTH0_' scripts/deploy-eks.sh
```

Confirmed the public Auth0 configuration embedded in the deployment script.

### Remove stale shell Auth0 configuration

```bash
unset AUTH0_CLIENT_ID
```

Prevented an old exported Client ID from overriding the intended SPA Client ID.

### Remove stale smoke-test tokens

```bash
unset ACCESS_TOKEN ASSISTANT_ACCESS_TOKEN
```

Prevented expired tokens from causing false authenticated smoke-test failures.

### Make the UI deployment script executable

```bash
chmod +x scripts/deploy-eks.sh
```

Required because the newly created script initially lacked executable mode.

### Fix Docker user to numeric UID

```bash
sed -i '' 's/^USER nextjs$/USER 1001/' Dockerfile
```

Changed the container image user to numeric UID 1001 so Kubernetes could verify `runAsNonRoot`.

### Verify Docker user

```bash
grep '^USER' Dockerfile
```

Confirmed that the Dockerfile now uses numeric UID 1001.

## Git

### Create the UI development branch

```bash
git switch -c dev
```

Created the long-lived development branch used for the UI work.

### Inspect UI changes

```bash
git status --short
```

Reviewed modified and new files after the replacement.

### Inspect change size

```bash
git diff --stat
```

Summarized the replacement’s file-level change volume.

### Stage all UI changes

```bash
git add -A
```

Staged the complete coherent UI replacement.

### Verify branch and latest commit

```bash
git status --short --branch && git log -1 --oneline
```

Confirmed a clean branch and displayed the latest commit.

### Commit agent companion changes

```bash
git add -A && git commit -m "Add authenticated UI companion support"
```

Committed assistant model catalog, selectable-model support, tests, docs, and deployment changes.

### Commit UI runtime and deployment fixes

```bash
git add Dockerfile scripts/deploy-eks.sh package-lock.json
git commit -m "Fix UI EKS runtime and deployment configuration"
```

Captured the numeric UID, deployment configuration, and public-registry lockfile fixes.

### Commit executable script mode

```bash
git add scripts/deploy-eks.sh
git commit -m "Make UI deployment script executable"
```

Preserved executable mode for future checkouts.

### Archive the agent repository

```bash
git archive \
  --format=zip \
  --prefix=johnny-johnny-agent/ \
  --output=../johnny-johnny-agent-iphone-session.zip \
  HEAD
```

Created a clean committed-source archive for the next iPhone session.

### Archive the UI repository

```bash
git archive \
  --format=zip \
  --prefix=johnny-johnny-ui/ \
  --output=../johnny-johnny-ui-iphone-session.zip \
  HEAD
```

Created a clean committed-source archive containing the proven web client contracts.

### Verify archives

```bash
unzip -l ../johnny-johnny-agent-iphone-session.zip | head -40
```

```bash
unzip -l ../johnny-johnny-ui-iphone-session.zip | head -40
```

Listed the first archive entries to verify structure and contents.

## npm / Node.js

### Clean deterministic install from lockfile

```bash
npm ci
```

Attempted an exact clean install from `package-lock.json`. This exposed private-registry references in the delivered lockfile.

### Verbose clean install

```bash
npm ci --loglevel verbose
```

Re-ran the install with registry and package-resolution output for diagnosis.

### Regenerate the lockfile against the public registry

```bash
rm -rf node_modules package-lock.json && npm install --registry=https://registry.npmjs.org/
```

Removed the unusable lockfile and dependencies, then installed from the public npm registry.

### Verbose public-registry reinstall

```bash
rm -rf node_modules package-lock.json && \
npm install --registry=https://registry.npmjs.org/ --loglevel verbose
```

Alternative diagnostic version of the public-registry reinstall.

### Verify internal registry references are gone

```bash
grep -c 'applied-caas-gateway1.internal.api.openai.org' package-lock.json
```

Expected and obtained `0`.

### Run UI tests

```bash
npm test
```

Ran the Node test suite; four tests passed.

### Run production build

```bash
npm run build
```

Imported thirty ADRs, built the Next.js application, and prepared the standalone runtime.

## Python / uv

### Run the full agent suite

```bash
uv run pytest
```

Validated the agent companion changes; 148 tests passed.

## rsync

### Preview agent companion copy

```bash
rsync -avhn \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'build/' \
  ../johnny-johnny-agent-new/ ./
```

Initial incremental preview. It was noisy because timestamps differed.

### Checksum-based agent preview

```bash
rsync -avhnc --itemize-changes \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'build/' \
  ../johnny-johnny-agent-new/ ./
```

Reported only content differences plus timestamp-only metadata differences.

### Apply checksum-based agent companion copy

```bash
rsync -avhc --itemize-changes \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'build/' \
  ../johnny-johnny-agent-new/ ./
```

Copied only meaningful companion updates into the canonical agent repository.

## Deployment Scripts

### Inspect agent and UI scripts

```bash
printf '\n===== AGENT FAST LOOP =====\n'
sed -n '1,260p' scripts/fast-loop.sh

printf '\n===== UI EKS DEPLOY =====\n'
sed -n '1,320p' ../johnny-johnny-ui/scripts/deploy-eks.sh
```

Displayed both deployment paths for comparison.

### Deploy the agent

```bash
./scripts/fast-loop.sh
```

Built, deployed, and smoke-tested the agent. It exposed stale-token and temporary ALB-routing issues.

### Deploy the UI

```bash
cd ../johnny-johnny-ui
./scripts/deploy-eks.sh
```

Built and pushed the UI image, applied Kubernetes resources, waited for rollout, and ran public smoke tests.

### Redeploy UI after clearing stale Client ID

```bash
unset AUTH0_CLIENT_ID
./scripts/deploy-eks.sh
```

Redeployed the UI using the intended Auth0 SPA Client ID.

## kubectl

### Inspect services, endpoints, and ingress

```bash
kubectl get svc,endpoints,ingress -n johnny-johnny -o wide
```

Confirmed the agent Service had an endpoint and showed that the old UI Service had none.

### Inspect the live shared ingress

```bash
kubectl get ingress johnny-johnny-ingress \
  -n johnny-johnny \
  -o yaml
```

Verified `/api/v1` routes to the agent and `/` routes to the UI.

### Test agent liveness inside the cluster

```bash
kubectl run jj-curl \
  --rm -i --restart=Never \
  --image=curlimages/curl \
  -n johnny-johnny \
  -- curl -i http://johnny-johnny-agent/api/v1/health/live
```

Proved that the agent Service returned HTTP 200 inside Kubernetes.

### Test agent readiness inside the cluster

```bash
kubectl run jj-curl \
  --rm -i --restart=Never \
  --image=curlimages/curl \
  -n johnny-johnny \
  -- curl -i http://johnny-johnny-agent/api/v1/health/ready
```

Was requested to verify the exact endpoint used by the ALB health check.

### Inspect UI pods

```bash
kubectl get pods -n johnny-johnny -l app=johnny-johnny-ui -o wide
```

Revealed `CreateContainerConfigError` for the new UI pod.

### Describe the failing UI pod

```bash
kubectl describe pod johnny-johnny-ui-<POD_SUFFIX> \
  -n johnny-johnny
```

The Events section showed that Kubernetes could not verify the named image user as non-root.

## HTTP / curl

### Verify backend liveness

```bash
curl -i https://johnny-johnny.mycroftai.org/api/v1/health/live
```

Checks the public agent endpoint through the shared ALB.

### Inspect deployed UI runtime configuration

```bash
curl -s https://johnny-johnny.mycroftai.org/runtime-config | python3 -m json.tool
```

Displayed the live public runtime configuration and exposed the stale Client ID.

### Print only the deployed Auth0 Client ID

```bash
curl -s https://johnny-johnny.mycroftai.org/runtime-config \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["auth0ClientId"])'
```

Verified which SPA Client ID the live UI was using.

### Verify ingress ALB and DNS target

```bash
printf 'Ingress ALB:\n'
kubectl get ingress johnny-johnny-ingress \
  -n johnny-johnny \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

printf '\n\nDNS target:\n'
dig +short johnny-johnny.mycroftai.org CNAME
```

Compares the live Ingress ALB hostname with the DNS target.

### Compare resolved IP addresses when Route 53 uses an Alias record

```bash
dig +short johnny-johnny.mycroftai.org
```

```bash
dig +short k8s-johnnyjo-johnnyjo-31a4af4980-1937427624.us-east-1.elb.amazonaws.com
```

Helps determine whether the public hostname resolves to the live Ingress ALB.

## File Editing

### Create the proposed production deployment configuration

```bash
mkdir -p docs/deployment/eks/config && nano docs/deployment/eks/config/production.env
```

Was proposed as a deterministic public SPA configuration file before choosing a temporary embedded-script approach.

## Useful Reference Commands

### View exact Auth0-related deployment logic

```bash
grep -nE 'AUTH0_|CLIENT_ID|runtime-config|env' ../johnny-johnny-ui/scripts/deploy-eks.sh
```

Finds the relevant variables and rendering path.

### Check for Route 53 behavior in deployment scripts

```bash
grep -nEi 'route53|change-resource-record|hosted-zone|dns' \
  ../johnny-johnny-agent/scripts/fast-loop.sh \
  scripts/deploy-eks.sh
```

Confirms whether the local scripts mutate DNS.

## Important Lessons

- Use `npm ci` only with a portable checked-in lockfile.
- Use numeric container users with Kubernetes `runAsNonRoot`.
- Do not let stale shell variables silently override deployment configuration.
- Mint fresh Auth0 tokens inside authenticated deployment smoke tests.
- A healthy Kubernetes Service does not guarantee a healthy ALB target group.
- During a shared-ingress migration, both routed Services need healthy endpoints.
