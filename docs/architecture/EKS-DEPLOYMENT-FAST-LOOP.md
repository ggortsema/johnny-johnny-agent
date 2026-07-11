# Johnny-Johnny EKS Deployment and Fast Loop

**Date:** July 10, 2026  
**Environment:** Development  
**Cluster:** `johnny-johnny-dev`  
**Region:** `us-east-1`  
**Namespace:** `johnny-johnny`

## Purpose

This document records the verified deployment contract for the Johnny-Johnny Python API.

## Public request path

```text
Client
→ Route 53
→ internet-facing AWS ALB
→ HTTPS listener using ACM
→ Kubernetes Ingress
→ ClusterIP Service port 80
→ Pod port 8000
→ FastAPI
→ PostgreSQL
```

## Runtime identity and secrets

```text
Kubernetes ServiceAccount
→ EKS Pod Identity association
→ IAM role
→ least-privilege IAM policy
→ AWS Secrets Manager
→ Secrets Store CSI Driver
→ mounted runtime secret files
```

Current runtime secrets:

```text
DATABASE_URL
GITHUB_TOKEN
OPENAI_API_KEY
```

Current non-secret assistant configuration:

```text
OPENAI_MODEL
```

Secret values must never be committed, printed into logs, placed in command cheat sheets, or sent to clients.

## Kubernetes resources

Expected repository layout:

```text
docs/deployment/eks/
├── iam/
│   ├── johnny-johnny-pod-identity-trust-policy.json
│   └── johnny-johnny-secrets-policy.json
└── kubernetes/
    ├── johnny-johnny-namespace.yml
    ├── johnny-johnny-agent-service-account.yml
    ├── johnny-johnny-secret-provider-class.yml
    ├── johnny-johnny-agent-deployment.yml
    ├── johnny-johnny-agent-service.yml
    └── johnny-johnny-ingress.yml
```

## Fast loop

Run:

```bash
./scripts/fast-loop.sh
```

The script:

1. validates required local commands and files;
2. runs the complete test suite;
3. refreshes EKS kubeconfig;
4. confirms the ECR repository;
5. authenticates Docker to ECR;
6. builds and pushes a `linux/amd64` image;
7. creates a unique tag from project version, Git SHA, and UTC timestamp;
8. renders the Deployment with that exact image;
9. applies namespace, ServiceAccount, SecretProviderClass, Service, Ingress, and Deployment;
10. captures the expected Deployment generation;
11. polls until the controller has observed that generation;
12. requires the final pod count to equal the desired replica count;
13. requires every final pod to use the exact new image;
14. requires every final pod to be ready;
15. validates liveness and readiness;
16. validates `401` without a token on backlog and assistant endpoints;
17. when `ACCESS_TOKEN` is set, validates authenticated backlog read access and the expected reconciliation authorization result;
18. when `ASSISTANT_ACCESS_TOKEN` is set, validates a public generated assistant response and its normalized response shape.

## Rollout completion contract

The loop is complete only when:

```text
current generation = expected generation
observed generation >= expected generation
total replicas = desired replicas
updated replicas = desired replicas
ready replicas = desired replicas
available replicas = desired replicas
unavailable replicas = 0
pod count = desired replicas
pods using exact image = desired replicas
ready pods = desired replicas
```

This avoids a false success where an old ready pod satisfies Deployment-level readiness while the new pod is still starting.

## Required pre-existing infrastructure

The fast loop assumes these already exist and are healthy:

- EKS cluster and worker nodes
- ECR repository
- EKS Pod Identity Agent
- Secrets Store CSI Driver
- AWS Secrets Store provider
- IAM policy and Pod Identity role
- EKS Pod Identity association
- AWS Secrets Manager values, including `OPENAI_API_KEY`
- AWS Load Balancer Controller
- Route 53 hosted zone
- ACM certificate and validation records

## Operational notes

- The cluster currently has two `t3.small` workers.
- The older UI and Java backend Deployments are scaled to zero.
- The older Services still exist.
- `johnny-johnny.mycroftai.org` currently routes directly to the Python agent.
- When the UI is ready, use `/` for the UI and `/api/v1` for the Python API.
- Updating a Secrets Manager value requires a pod restart because the process exports mounted values only at startup.
- The assistant smoke token must grant `invoke:assistant` and is supplied only to the local fast-loop process through `ASSISTANT_ACCESS_TOKEN`.
- `OPENAI_MODEL` is non-secret Deployment configuration and can be changed independently of the public endpoint.
- `kubectl get ingress` may continue showing port 80 even when the ALB has both HTTP and HTTPS listeners; use the ELBv2 API to inspect the authoritative listener state.

## Failure lessons captured

### Invalid database URL

A literal `echo` prefix was accidentally stored in `DATABASE_URL`. The pod remained running, liveness passed, and readiness failed. This demonstrated why database readiness is a deployment gate.

### AWS CLI table rendering

A JMESPath query combining a scalar and nested rows failed under `--output table`. Query the overall status and per-domain validation separately.

### Incorrect project identity

A protected read using `johnny-johnny` returned a domain-level `404`, proving authentication had succeeded but the stored provider project title was wrong. The correct stored project is:

```text
Johnny-Johnny Backlog Persistence Sandbox
```

### Curl `-f`

`curl -f` correctly failed on an expected `403`, but hid the structured error body. Use `-i` without `-f` when inspecting expected authorization failures.
