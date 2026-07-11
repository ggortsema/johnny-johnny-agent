# Development Documentation

This directory contains Johnny-Johnny engineering guidance and durable session artifacts.

Core guidance:

- `WORKING_AGREEMENT.md` — how contributors collaborate.
- `ENGINEERING_PRINCIPLES.md` — software design principles.
- `DECISION_LOG.md` — lightweight historical decisions.
- `backlog-persistence-test-strategy.md` — automated and live validation strategy.
- `ENGINEERING-SESSION-CLOSURE.md` — engineering-session closure checklist.

Current implementation and handoff artifacts:

- `../api/backlog-rest-api.md` — secured v1 authentication, authorization, endpoint, execution-mode, and error contracts.
- `security-implementation-summary-2026-07-10.md` — Auth0 implementation inventory and verification evidence.
- `rest-api-implementation-summary-2026-07-10.md` — original REST adapter implementation inventory.
- `backlog-session-update-plan-2026-07-10.md` — canonical story completion commands and EKS/webhook sequence.
- `commands-left-off.txt` — immediate commands for Auth0 smoke testing and EKS preparation.
- `session-index.md` — current session navigation and next-story handoff.

Architecture and deployment:

- `../architecture/adrs/ADR-004-separate-human-and-webhook-authentication-boundaries.md`
- `../architecture/adrs/ADR-005-auth0-access-token-and-permission-policy.md`
- `../architecture/api-security-deployment-and-client-evolution.md`
- `../deployment/eks-fast-testing-loop.md`

Major architectural decisions live under:

```text
docs/architecture/adrs/
```
