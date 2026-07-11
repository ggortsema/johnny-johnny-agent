# Command Cheat Sheet — July 10, 2026

This sheet records the shell commands used during the Johnny-Johnny manual Docker/ECR/EKS deployment session.

## Docker

### Run the locally built container

```bash
docker run --rm   --name johnny-johnny-agent   --env-file .env   -p 8000:8000   johnny-johnny-agent:local
```

- `docker run` starts a container from an image.
- `--rm` deletes the stopped container automatically.
- `--name` assigns a readable container name.
- `--env-file .env` injects environment variables from `.env`.
- `-p 8000:8000` maps host port 8000 to container port 8000.

### Authenticate Docker to ECR

```bash
aws ecr get-login-password   --region us-east-1 | docker login   --username AWS   --password-stdin 359546647832.dkr.ecr.us-east-1.amazonaws.com
```

- AWS prints a temporary registry password.
- `|` pipes that password into Docker.
- `--password-stdin` avoids exposing it in shell history.

Manual equivalent:

```bash
aws ecr get-login-password --region us-east-1
```

Then:

```bash
docker login   --username AWS   359546647832.dkr.ecr.us-east-1.amazonaws.com
```

### Build an amd64 image and push directly to ECR

```bash
docker buildx build   --platform linux/amd64   --tag 359546647832.dkr.ecr.us-east-1.amazonaws.com/johnny-johnny/johnny-johnny-agent:0.1.0   --push   .
```

- `buildx build` supports cross-platform builds.
- `--platform linux/amd64` matches the EKS x86_64 nodes.
- `--tag` assigns the full ECR image name.
- `--push` uploads after building.
- `.` uses the current directory as the Docker build context.

## curl

### Check liveness locally

```bash
curl -i http://127.0.0.1:8000/api/v1/health/live
```

- `-i` includes HTTP response headers.
- Calls the public liveness endpoint.

### Call a protected endpoint

```bash
curl -i   -H "Authorization: Bearer ${ACCESS_TOKEN}"   http://127.0.0.1:8000/api/v1/auth/whoami
```

- `-H` adds an HTTP header.
- Sends an OAuth bearer access token.

## AWS EKS

### Describe the cluster

```bash
aws eks describe-cluster   --name johnny-johnny-dev   --region us-east-1   --query 'cluster.{Status:status,Endpoint:endpoint,Version:version}'   --output table
```

- Confirms cluster existence, status, endpoint, and Kubernetes version.
- `--query` selects only useful fields.
- `--output table` formats the result.

### Refresh kubeconfig

```bash
aws eks update-kubeconfig   --name johnny-johnny-dev   --region us-east-1
```

- Updates local kubeconfig with the current EKS API endpoint and auth settings.

### List node groups

```bash
aws eks list-nodegroups   --cluster-name johnny-johnny-dev   --region us-east-1   --output table
```

### Inspect node group sizing

```bash
aws eks describe-nodegroup   --cluster-name johnny-johnny-dev   --nodegroup-name ng-7996e69b   --region us-east-1   --query 'nodegroup.{Status:status,InstanceTypes:instanceTypes,ScalingConfig:scalingConfig}'   --output table
```

### Scale the node group

```bash
aws eks update-nodegroup-config   --cluster-name johnny-johnny-dev   --nodegroup-name ng-7996e69b   --region us-east-1   --scaling-config minSize=1,maxSize=2,desiredSize=2
```

- Keeps at least one node.
- Allows up to two.
- Requests two running nodes now.

### Install the Pod Identity Agent add-on

```bash
aws eks create-addon   --cluster-name johnny-johnny-dev   --addon-name eks-pod-identity-agent   --region us-east-1
```

### Check add-on status

```bash
aws eks describe-addon   --cluster-name johnny-johnny-dev   --addon-name eks-pod-identity-agent   --region us-east-1   --query 'addon.status'   --output text
```

### Create a Pod Identity association

```bash
aws eks create-pod-identity-association   --cluster-name johnny-johnny-dev   --namespace johnny-johnny   --service-account johnny-johnny-agent   --role-arn arn:aws:iam::359546647832:role/JohnnyJohnnyAgentPodIdentityRole   --region us-east-1
```

- Associates a Kubernetes ServiceAccount with an IAM role.

### List Pod Identity associations

```bash
aws eks list-pod-identity-associations   --cluster-name johnny-johnny-dev   --namespace johnny-johnny   --service-account johnny-johnny-agent   --region us-east-1   --query 'associations[].{AssociationId:associationId,Namespace:namespace,ServiceAccount:serviceAccount}'   --output table
```

## AWS ECR

### List repositories

```bash
aws ecr describe-repositories   --region us-east-1   --query 'repositories[].repositoryName'   --output table
```

Compact version:

```bash
aws ecr describe-repositories   --region us-east-1   --query 'repositories[].repositoryName'   --output text
```

### Create a repository

```bash
aws ecr create-repository   --repository-name johnny-johnny/johnny-johnny-agent   --region us-east-1   --image-scanning-configuration scanOnPush=true   --image-tag-mutability MUTABLE
```

- Creates the registry repository.
- Enables vulnerability scanning on push.
- Allows tags to be replaced.

### Describe a specific repository

```bash
aws ecr describe-repositories   --repository-names johnny-johnny/johnny-johnny-agent   --region us-east-1
```

### Verify an image in ECR

```bash
aws ecr describe-images   --repository-name johnny-johnny/johnny-johnny-agent   --region us-east-1   --image-ids imageTag=0.1.0   --query 'imageDetails[0].{Tags:imageTags,Digest:imageDigest,Size:imageSizeInBytes,Pushed:imagePushedAt}'   --output table
```

- Confirms the image tag exists.
- Shows immutable digest, size, and push time.

## AWS Secrets Manager

### List secret names

```bash
aws secretsmanager list-secrets   --region us-east-1   --query 'SecretList[].Name'   --output table
```

### Hidden shell prompt for a secret

```bash
read -s -p "DATABASE_URL: " DATABASE_URL_SECRET
```

- `read` stores input in a shell variable.
- `-s` disables visible echo.
- `-p` displays a prompt.
- Press Enter after pasting the value.

GitHub equivalent:

```bash
read -s -p "GITHUB_TOKEN: " GITHUB_TOKEN_SECRET
```

### Create a secret from a shell variable

```bash
aws secretsmanager create-secret   --name DATABASE_URL   --region us-east-1   --secret-string "$DATABASE_URL_SECRET"
```

GitHub equivalent:

```bash
aws secretsmanager create-secret   --name GITHUB_TOKEN   --region us-east-1   --secret-string "$GITHUB_TOKEN_SECRET"
```

### Clear the shell variable

```bash
unset DATABASE_URL_SECRET
```

```bash
unset GITHUB_TOKEN_SECRET
```

### Restore terminal echo

```bash
stty echo
```

- Re-enables visible typing if `read -s` leaves terminal echo disabled.

### Reset the terminal

```bash
reset
```

- Reinitializes terminal display and input settings.

### Describe a secret without showing its value

```bash
aws secretsmanager describe-secret   --secret-id DATABASE_URL   --region us-east-1   --query '{Name:Name,ARN:ARN,LastChangedDate:LastChangedDate}'   --output table
```

### Retrieve a secret ARN

```bash
aws secretsmanager describe-secret   --secret-id DATABASE_URL   --region us-east-1   --query 'ARN'   --output text
```

GitHub equivalent:

```bash
aws secretsmanager describe-secret   --secret-id GITHUB_TOKEN   --region us-east-1   --query 'ARN'   --output text
```

### Update an existing secret

```bash
aws secretsmanager put-secret-value   --secret-id DATABASE_URL   --region us-east-1   --secret-string "$DATABASE_URL_SECRET"
```

- Creates a new secret version while keeping the same secret name and ARN.

## AWS IAM

### Create an IAM policy from a JSON file

```bash
aws iam create-policy   --policy-name JohnnyJohnnyRuntimeSecretsRead   --description "Allows Johnny-Johnny dev pods to read required runtime secrets"   --policy-document file://johnny-johnny-secrets-policy.json
```

- `file://` tells the AWS CLI to read JSON from a local file.

### Create an IAM role

```bash
aws iam create-role   --role-name JohnnyJohnnyAgentPodIdentityRole   --description "Pod Identity role for the Johnny-Johnny agent in EKS"   --assume-role-policy-document file://johnny-johnny-pod-identity-trust-policy.json
```

### Attach a managed policy to a role

```bash
aws iam attach-role-policy --role-name JohnnyJohnnyAgentPodIdentityRole --policy-arn arn:aws:iam::359546647832:policy/JohnnyJohnnyRuntimeSecretsRead
```

### Verify attached role policies

```bash
aws iam list-attached-role-policies --role-name JohnnyJohnnyAgentPodIdentityRole --query 'AttachedPolicies[].{Name:PolicyName,Arn:PolicyArn}' --output table
```

## kubectl — Cluster and Nodes

### List nodes

```bash
kubectl get nodes -o wide
```

- Shows node readiness, IPs, OS, kernel, and container runtime.

### Watch node changes

```bash
kubectl get nodes -w
```

- `-w` watches continuously.
- Stop with `Ctrl-C`.

### Show node pod capacity

```bash
kubectl get node ip-192-168-55-189.ec2.internal   -o jsonpath='{.status.capacity.pods}{" capacity / "}{.status.allocatable.pods}{" allocatable
"}'
```

### Show pods assigned to one node

```bash
kubectl get pods -A   --field-selector spec.nodeName=ip-192-168-55-189.ec2.internal   -o wide
```

- `-A` means all namespaces.
- `--field-selector` filters by node assignment.

## kubectl — Namespaces and ServiceAccounts

### Check a namespace

```bash
kubectl get namespace johnny-johnny
```

### Create a namespace

```bash
kubectl create namespace johnny-johnny
```

### Create a ServiceAccount

```bash
kubectl create serviceaccount johnny-johnny-agent   --namespace johnny-johnny
```

## kubectl — Add-ons and System Workloads

### Check Pod Identity Agent

```bash
kubectl get daemonset   -n kube-system   eks-pod-identity-agent
```

### Find secret-related DaemonSets

```bash
kubectl get daemonsets -n kube-system | grep -E 'secrets-store|secrets-provider'
```

### Find secret-related pods

```bash
kubectl get pods -n kube-system | grep -E 'secrets-store|secrets-provider'
```

### Inspect the CSI driver pods

```bash
kubectl get pods -n kube-system -l app=secrets-store-csi-driver -o wide
```

### Inspect a pod in detail

```bash
kubectl describe pod secrets-store-csi-driver-upgrade-crds-lj56j -n kube-system
```

- Shows scheduling, mounts, container state, and Events.

### Inspect recent Kubernetes events

```bash
kubectl get events -n kube-system   --sort-by='.lastTimestamp'   | tail -30
```

### Inspect a Job

```bash
kubectl get job secrets-store-csi-driver-upgrade-crds   -n kube-system
```

### Inspect pods belonging to a Job

```bash
kubectl get pods   -n kube-system   -l job-name=secrets-store-csi-driver-upgrade-crds   -o wide
```

### Delete a stale Job

```bash
kubectl delete job secrets-store-csi-driver-upgrade-crds -n kube-system --ignore-not-found
```

- `--ignore-not-found` avoids an error if already absent.

### Search multiple resource types

```bash
kubectl get job,pod,serviceaccount -n kube-system | grep secrets-store
```

## Helm

### Add the AWS secrets chart repository

```bash
helm repo add aws-secrets-manager   https://aws.github.io/secrets-store-csi-driver-provider-aws
```

### Refresh chart indexes

```bash
helm repo update
```

### Install the AWS secrets provider and CSI driver

```bash
helm install secrets-provider-aws   aws-secrets-manager/secrets-store-csi-driver-provider-aws   --namespace kube-system
```

### Install with waiting and timeout

```bash
helm install secrets-provider-aws   aws-secrets-manager/secrets-store-csi-driver-provider-aws   --namespace kube-system   --wait   --timeout 10m
```

- `--wait` waits for resources to become ready.
- `--timeout 10m` limits the wait to ten minutes.

### List Helm releases

```bash
helm list -n kube-system
```

### Inspect release status

```bash
helm status secrets-provider-aws -n kube-system
```

### Uninstall a release

```bash
helm uninstall secrets-provider-aws -n kube-system
```

## kubectl — Application Deployment

### List Deployments

```bash
kubectl get deployments -n johnny-johnny
```

### Scale old Deployments to zero

```bash
kubectl scale deployment johnny-johnny-ui johnny-johnny-backend --replicas=0 --namespace johnny-johnny
```

- Keeps the Deployment definitions but stops their pods.

### Apply a manifest

```bash
kubectl apply -f johnny-johnny-secret-provider-class.yml
```

```bash
kubectl apply -f johnny-johnny-agent-deployment.yml
```

- Declaratively creates or updates Kubernetes resources.

### Verify a SecretProviderClass

```bash
kubectl get secretproviderclass johnny-johnny-agent-secrets --namespace johnny-johnny
```

### Wait for rollout completion

```bash
kubectl rollout status deployment/johnny-johnny-agent --namespace johnny-johnny
```

- Blocks until rollout succeeds or fails.
- Stop with `Ctrl-C`.

### Poll Deployment state

```bash
kubectl get deployment johnny-johnny-agent -n johnny-johnny
```

- Preferred during this session over indefinite waiting.

### Poll application pods

```bash
kubectl get pods -n johnny-johnny -l app=johnny-johnny-agent
```

### Show pod details and probe failures

```bash
kubectl describe pod johnny-johnny-agent-575bddfb67-t5bs6 -n johnny-johnny
```

### View application logs

```bash
kubectl logs johnny-johnny-agent-575bddfb67-t5bs6 -n johnny-johnny
```

### Execute a readiness check inside the pod

```bash
kubectl exec -n johnny-johnny johnny-johnny-agent-575bddfb67-t5bs6 -- python -c 'import urllib.request, urllib.error; u="http://127.0.0.1:8000/api/v1/health/ready"; 
try:
 print(urllib.request.urlopen(u).read().decode())
except urllib.error.HTTPError as e:
 print(e.read().decode())'
```

- Runs Python inside the container.
- Prints the HTTP response body even for a 503.

### Check mounted secret file sizes without showing values

```bash
kubectl exec -n johnny-johnny johnny-johnny-agent-575bddfb67-t5bs6 -- sh -c 'for f in /mnt/secrets-store/*; do printf "%s: %s bytes
" "$(basename "$f")" "$(wc -c < "$f")"; done'
```

### Inspect PID 1 environment

```bash
kubectl exec -n johnny-johnny johnny-johnny-agent-575bddfb67-t5bs6 -- sh -c 'tr "\0" "\n" < /proc/1/environ'
```

- Shows the environment of the actual running server process.
- This can expose secrets; do not paste output into chat.

### Restart the Deployment after a secret change

```bash
kubectl rollout restart deployment/johnny-johnny-agent -n johnny-johnny
```

## Bash and Shell Syntax

### Create a file with a heredoc

```bash
cat > filename <<'EOF'
file contents
EOF
```

- `cat > filename` writes standard input into a file.
- `<<'EOF'` begins a literal heredoc.
- The final `EOF` ends it.
- Quoted `EOF` prevents shell variable expansion inside the file.

### Print a file

```bash
cat johnny-johnny-secrets-policy.json
```

### Print a newline

```bash
printf '\n'
```

### Test terminal output

```bash
echo ok
```

### Cancel an incomplete or running command

```text
Ctrl-C
```

- Cancels the foreground process or unfinished shell command.

### Bash continuation prompt

```text
>
```

This means Bash believes the command is incomplete, often because of:

- an unmatched quote
- a trailing backslash
- an unfinished parenthesis
- an unfinished heredoc

Use `Ctrl-C` to cancel and return to the normal prompt.

## Files Created with Heredocs

### IAM secrets policy

```bash
cat > johnny-johnny-secrets-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadJohnnyJohnnyRuntimeSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:359546647832:secret:DATABASE_URL-kwT9cC",
        "arn:aws:secretsmanager:us-east-1:359546647832:secret:GITHUB_TOKEN-eyDU2F"
      ]
    }
  ]
}
EOF
```

### Pod Identity role trust policy

```bash
cat > johnny-johnny-pod-identity-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
EOF
```

### SecretProviderClass manifest

```bash
cat > johnny-johnny-secret-provider-class.yml <<'EOF'
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: johnny-johnny-agent-secrets
  namespace: johnny-johnny
spec:
  provider: aws
  parameters:
    usePodIdentity: "true"
    objects: |
      - objectName: "DATABASE_URL"
        objectType: "secretsmanager"
        objectAlias: "DATABASE_URL"
      - objectName: "GITHUB_TOKEN"
        objectType: "secretsmanager"
        objectAlias: "GITHUB_TOKEN"
EOF
```

### Johnny-Johnny Deployment manifest

```bash
cat > johnny-johnny-agent-deployment.yml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: johnny-johnny-agent
  namespace: johnny-johnny
spec:
  replicas: 1
  selector:
    matchLabels:
      app: johnny-johnny-agent
  template:
    metadata:
      labels:
        app: johnny-johnny-agent
    spec:
      serviceAccountName: johnny-johnny-agent
      containers:
        - name: johnny-johnny-agent
          image: 359546647832.dkr.ecr.us-east-1.amazonaws.com/johnny-johnny/johnny-johnny-agent:0.1.0
          imagePullPolicy: Always
          command:
            - /bin/sh
            - -c
          args:
            - |
              export DATABASE_URL="$(cat /mnt/secrets-store/DATABASE_URL)"
              export GITHUB_TOKEN="$(cat /mnt/secrets-store/GITHUB_TOKEN)"
              exec jj serve --host 0.0.0.0 --port 8000
          env:
            - name: AUTH0_DOMAIN
              value: "dev-ude3gljkecu7ylzt.us.auth0.com"
            - name: AUTH0_AUDIENCE
              value: "https://johnny-johnny.mycroftai.org"
            - name: JOHNNY_JOHNNY_API_DOCS_ENABLED
              value: "false"
            - name: AUTH0_CLOCK_SKEW_SECONDS
              value: "30"
            - name: AUTH0_JWKS_TIMEOUT_SECONDS
              value: "5"
            - name: AUTH0_JWKS_CACHE_SECONDS
              value: "300"
          ports:
            - name: http
              containerPort: 8000
          readinessProbe:
            httpGet:
              path: /api/v1/health/ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/v1/health/live
              port: http
            initialDelaySeconds: 10
            periodSeconds: 20
          volumeMounts:
            - name: runtime-secrets
              mountPath: /mnt/secrets-store
              readOnly: true
      volumes:
        - name: runtime-secrets
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: johnny-johnny-agent-secrets
EOF
```

## Git

No new Git commands were executed during this deployment segment. The repository was already on `dev`, and the new local deployment files have not yet been reviewed or committed.

At the next suitable checkpoint, useful Git commands will likely include:

```bash
git status --short --branch
```

- Shows branch, changed files, and upstream status.

```bash
git add Dockerfile .dockerignore johnny-johnny-secrets-policy.json johnny-johnny-pod-identity-trust-policy.json johnny-johnny-secret-provider-class.yml johnny-johnny-agent-deployment.yml
```

- Stages selected files.

```bash
git commit -m "Add manual EKS deployment manifests"
```

- Creates a local commit.

These were not run yet and are included only as likely next steps, not as completed commands.
