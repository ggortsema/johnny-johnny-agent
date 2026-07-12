# Assistant Response Endpoint Deployment Acceptance

**Date:** July 11, 2026  
**Story:** `implement-assistant-response-endpoint`  
**Status:** Done  
**Environment:** Public Johnny-Johnny EKS deployment

## Summary

The first provider-neutral Johnny-Johnny assistant endpoint was implemented, copied into the canonical Git repository, tested, deployed to EKS, authorized through Auth0, and validated through a live OpenAI request.

Public route:

```http
POST /api/v1/assistant/responses
Authorization: Bearer <token with invoke:assistant>
Content-Type: application/json
```

The route remains an assistant-orchestration boundary rather than an OpenAI proxy:

```text
HTTP route
→ GenerateAssistantResponse
→ LanguageModelProvider
→ OpenAILanguageModelProvider
→ OpenAI Responses API
→ normalized Johnny-Johnny response
```

Retrieval, memory, prompt construction, tool execution, and provider selection can therefore be added behind the existing endpoint without requiring clients to adopt a new ordinary request/response route.

## Repository Integration

The generated implementation was unpacked beside the canonical repository as:

```text
johnny-johnny-agent-2
```

Its contents were copied into:

```text
johnny-johnny-agent
```

The canonical repository retained:

- its `.git` directory and history;
- the existing `dev` branch;
- the local `.env`;
- existing generated test reports under `build/`.

An initial `rsync --delete` dry run correctly revealed that `.env` and `build/` would have been removed. The actual copy omitted deletion behavior and excluded those paths.

## Test Evidence

The full test suite passed in the canonical repository:

```text
138 passed
```

Whitespace validation also passed:

```bash
git diff --check
```

with no output.

The implementation was committed on `dev` with:

```text
Implement assistant response endpoint
```

## AWS and EKS Acceptance

The existing AWS Secrets Manager secret named:

```text
OPENAI_API_KEY
```

was retained as the authoritative known-working secret. The local text file was not used to overwrite it.

The pod identity role was confirmed as:

```text
JohnnyJohnnyAgentPodIdentityRole
```

The attached managed policy was confirmed as:

```text
JohnnyJohnnyRuntimeSecretsRead
```

A new default managed-policy version was created:

```text
v2
```

It grants the runtime access to:

```text
arn:aws:secretsmanager:us-east-1:359546647832:secret:OPENAI_API_KEY-*
```

The committed fast-loop deployment contract was then run successfully:

```bash
./scripts/fast-loop.sh
```

This deployed the new image and applied the updated Kubernetes secret projection and Deployment configuration.

## Auth0 Acceptance

The capability-specific permission was added to the Johnny-Johnny API:

```text
invoke:assistant
```

The permission was granted to the existing M2M smoke-test application. A fresh token was obtained because previously issued tokens do not gain newly granted scopes.

The token was verified to contain:

```json
{
  "scopes": [
    "invoke:assistant",
    "read:backlogs",
    "write:backlogs"
  ]
}
```

## Public Live Acceptance Test

Request:

```json
{
  "text": "Reply with one sentence confirming that the Johnny-Johnny assistant endpoint is working."
}
```

Successful public response:

```json
{
  "response_id": "resp_0bb32f330b131ac2016a51ea7b7f60819fa1309affcd2d13af",
  "text": "The Johnny-Johnny assistant endpoint is working.",
  "model": "gpt-5.6-sol",
  "usage": {
    "input_tokens": 22,
    "output_tokens": 14
  }
}
```

This proves the complete deployed path:

```text
Auth0 access token
→ public HTTPS endpoint
→ EKS
→ FastAPI authorization
→ GenerateAssistantResponse
→ OpenAI provider adapter
→ OpenAI
→ normalized response
```

## Acceptance Criteria Result

- [x] The endpoint accepts a non-empty `text` field.
- [x] A valid bearer token is required.
- [x] `invoke:assistant` is required.
- [x] The route invokes an application use case rather than the OpenAI SDK directly.
- [x] The use case depends on a provider-neutral port.
- [x] The OpenAI adapter is isolated behind the port.
- [x] The OpenAI Responses API is used.
- [x] The response is normalized and provider-neutral.
- [x] `OPENAI_API_KEY` is delivered through AWS Secrets Manager and the existing pod identity/CSI path.
- [x] `OPENAI_MODEL` is external non-secret configuration.
- [x] Unit and behavior tests cover the implementation.
- [x] The full test suite passes.
- [x] The fast loop deploys the image.
- [x] A public authenticated request returns generated text.

## Decisions Confirmed During Acceptance

### AWS is the runtime secret source of truth

A local key text file must not overwrite an existing known-working AWS secret merely because the local file is available. Runtime secret management remains authoritative in AWS Secrets Manager.

### Browser authentication is not M2M authentication

The future web UI must not embed or use the M2M client secret. It should use an Auth0 Single Page Application with Authorization Code Flow and PKCE, request the Johnny-Johnny API audience, and receive user-scoped permissions.

### Initial chat remains backend-stateless

The first chat UI may keep a visible transcript in browser state, but it should send only the current user message. It must not silently move prompt assembly or conversation orchestration into the client. Backend conversation persistence can later be added through an optional `conversation_id` behind the same assistant endpoint.

## Next Story

Suggested story:

```text
Update the existing Johnny-Johnny web UI to authenticate users through Auth0
and exercise the deployed agent API, including an initial stateless assistant
chat interface.
```

The user will provide UI guidelines and desired behavior at the beginning of the next engineering session.
