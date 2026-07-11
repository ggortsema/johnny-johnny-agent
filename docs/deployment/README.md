# Deployment Documentation

Johnny-Johnny's REST API is secured with Auth0 and is ready for the EKS deployment story.

Current deployment design:

- `eks-fast-testing-loop.md` — required EKS resources, secret boundary, probe behavior, and the contract for the build/deploy/smoke-test Bash loop

No production Kubernetes manifest or deployment script is claimed as implemented in the security story. Those artifacts belong to `deploy-johnny-johnny-api-to-eks` and must be validated against the selected AWS account, cluster, ingress, certificate, secret manager, and PostgreSQL networking.
