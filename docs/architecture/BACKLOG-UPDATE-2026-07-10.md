# Backlog Update Proposal

**Date:** July 10, 2026

## Complete

### `deploy-johnny-johnny-api-to-eks`

Suggested status:

```text
Done
```

Completion evidence:

- Python API deployed to EKS.
- Runtime secrets delivered from AWS Secrets Manager through EKS Pod Identity and the Secrets Store CSI Driver.
- PostgreSQL readiness passed.
- Internal ClusterIP Service path passed.
- Existing ALB and Ingress were updated to route `johnny-johnny.mycroftai.org` to the Python agent.
- ACM certificate issued and attached.
- HTTP redirects to HTTPS.
- Public liveness returned `200`.
- Missing token returned `401`.
- Valid read token returned `200`.
- Valid token without reconciliation permission returned `403`.
- Versioned image fast loop completed successfully.
- Strengthened rollout gate verified the new generation and exact image.

## Ready

### `implement-assistant-response-endpoint`

Goal:

```text
authenticated text input
→ Johnny-Johnny application use case
→ OpenAI provider adapter
→ normalized text response
```

See `ASSISTANT-RESPONSE-ENDPOINT-STORY.md`.

## Deferred

### Integrate the proven EKS deployment path into StyxCD

Defer until the user's pre-employment goals are complete.

The Bash loop remains the executable reference implementation, not the permanent orchestration platform.

## Following story

### Build minimal Johnny-Johnny web UI

The first UI should provide:

- hosted Auth0 login;
- a text input;
- submit action;
- assistant response display;
- loading and error states;
- direct use of the Johnny-Johnny API rather than OpenAI;
- a foundation for later RAG testing.

The native iPhone controller remains a primary product path and should evolve alongside the web UI after the first browser-based interaction is proven.
