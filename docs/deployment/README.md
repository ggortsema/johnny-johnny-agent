# Deployment Documentation

Johnny-Johnny's Auth0-secured Python API is deployed to EKS through a tested manual fast loop.

Current deployment artifacts:

- `eks-fast-testing-loop.md` — general resource, secret, probe, rollout, and smoke-test contract;
- `../architecture/EKS-DEPLOYMENT-FAST-LOOP.md` — verified environment-specific deployment contract;
- `eks/kubernetes/` — namespace, ServiceAccount, SecretProviderClass, Deployment, Service, and Ingress manifests;
- `eks/iam/` — Pod Identity trust and least-privilege runtime secret access policies;
- `../../scripts/fast-loop.sh` — executable build, push, apply, rollout, and public smoke-test path.

Assistant endpoint additions:

- `OPENAI_API_KEY` is projected from AWS Secrets Manager through Pod Identity and Secrets Store CSI;
- `OPENAI_MODEL` is non-secret Deployment configuration;
- the fast loop always proves an unauthenticated assistant call returns `401`;
- when `ASSISTANT_ACCESS_TOKEN` is supplied, the loop proves authenticated generation returns a normalized `200` response.

The AWS secret value, Auth0 permission grant, deployment, and live assistant smoke are environment operations and are not implied merely by committing these artifacts.
