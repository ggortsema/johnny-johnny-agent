# ADR: Johnny-Johnny EKS Runtime and Public API Boundary

**Date:** July 10, 2026  
**Status:** Accepted  
**Project:** Johnny-Johnny Agent

## Context

Johnny-Johnny needed a proven deployment path for its Python API before that path could be automated or integrated into StyxCD. The deployment had to support:

- EKS runtime deployment
- AWS-managed runtime secrets
- PostgreSQL readiness
- public HTTPS access
- OAuth 2.0 authentication and scope authorization
- future web and native iPhone clients
- future GitHub webhook ingress
- a repeatable developer deployment loop

An older Johnny-Johnny UI and Java backend already existed in the cluster behind an AWS Application Load Balancer.

## Decision

### Runtime

Deploy the Python `johnny-johnny-agent` application to the `johnny-johnny-dev` EKS cluster as a Kubernetes Deployment.

The Python API replaces the Java backend as the active Johnny-Johnny backend. The Java Deployment remains scaled to zero while the replacement path is developed.

### Runtime secrets

Use:

```text
AWS Secrets Manager
→ EKS Pod Identity
→ Secrets Store CSI Driver
→ AWS Secrets Store provider
→ SecretProviderClass
→ read-only mounted files
→ process environment exported at container startup
```

Do not copy runtime secrets into Kubernetes Secret objects.

The workload IAM policy is restricted to the exact Johnny-Johnny secret ARNs and the actions required to read and describe them.

### Network boundary

Reuse the existing internet-facing ALB and Kubernetes Ingress rather than creating a temporary second ALB.

During the API-only phase:

```text
https://johnny-johnny.mycroftai.org/
→ johnny-johnny-agent Service:80
→ Pod:8000
```

When the web UI is ready, evolve the same application boundary to:

```text
/
→ web UI

/api/v1/
→ Python API
```

### TLS and DNS

Use an ACM certificate covering:

```text
mycroftai.org
*.mycroftai.org
styxcd.com
*.styxcd.com
```

The certificate is attached to the existing ALB HTTPS listener. Port 80 redirects to port 443.

The selected hostname is `johnny-johnny.mycroftai.org`, which is covered by `*.mycroftai.org`.

### Authentication and authorization

Use Auth0 OAuth 2.0 bearer tokens.

The public deployment must demonstrate:

```text
public liveness                     → 200
protected endpoint without token   → 401
protected read with valid scope    → 200
valid token missing admin scope    → 403
```

### Deployment automation

Keep `scripts/fast-loop.sh` as a temporary executable proof of the deployment contract:

```text
test
→ build linux/amd64 image
→ push versioned image to ECR
→ apply application manifests
→ observe the new Deployment generation
→ prove every remaining pod uses the new image
→ wait for readiness
→ run public and OAuth smoke tests
```

The Bash implementation is not the long-term orchestration platform. It is a verified reference implementation and future StyxCD integration input.

### StyxCD integration

Defer StyxCD integration to a separate story. Do not hide cluster capability setup, workload identity, runtime secret delivery, application deployment, and validation inside one monolithic deploy step.

The expected StyxCD capability split is:

```text
cluster capabilities
application identity
runtime secret projection
application deployment
network exposure
rollout observation
post-deployment verification
```

## Consequences

### Positive

- The public deployment path has been verified end to end.
- Secrets remain AWS-managed and are not persisted in Kubernetes Secrets.
- Web and iPhone clients can share one stable API boundary.
- The deployment contract is concrete enough to automate safely.
- The existing ALB is reused, avoiding temporary infrastructure and cost.
- The Bash fast loop exposes the stages and failure gates StyxCD must eventually model.

### Tradeoffs

- The current fast loop is intentionally imperative and should not become the permanent platform.
- The existing UI and Java resources still exist and must be retired or repurposed deliberately.
- The Deployment currently exports mounted secrets at process startup, so a secret change requires a pod restart.
- Cluster add-ons, IAM policy, IAM role, Pod Identity association, certificate issuance, and DNS validation remain prerequisite infrastructure rather than fast-loop operations.

## Validation

The following were successfully validated:

- PostgreSQL-backed readiness
- internal Service-to-Pod traffic
- ALB HTTPS listener and certificate
- HTTP-to-HTTPS redirect
- public liveness
- Auth0 token validation
- authenticated backlog read
- insufficient-scope denial
- versioned image deployment
- generation-aware rollout polling
- exact-image pod verification
