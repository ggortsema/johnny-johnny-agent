# Story: Implement Minimal Assistant Response Endpoint

**Date Drafted:** July 10, 2026  
**Suggested ID:** `implement-assistant-response-endpoint`  
**Suggested Status:** Ready  
**Suggested Epic:** AI Assistant / RAG Foundation

## Goal

Add one authenticated Johnny-Johnny API endpoint that accepts text, sends it through a language-model provider boundary, and returns normalized generated text.

This is the smallest backend capability needed before building the web UI. The UI will then become the interactive test harness for later RAG work.

## User value

A web or native client can send natural-language text to Johnny-Johnny and receive an AI-generated response without holding or exposing an OpenAI API key.

## Public contract

```http
POST /api/v1/assistant/responses
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "text": "Explain what this backlog item is trying to accomplish."
}
```

Response:

```json
{
  "response_id": "provider-or-canonical-response-id",
  "text": "Generated response text.",
  "model": "configured-model-name",
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

The public contract must remain provider-neutral. Do not return the raw OpenAI response object.

## Internal design

```text
API route
→ GenerateAssistantResponse use case
→ LanguageModelProvider port
→ OpenAI language-model adapter
→ normalized domain/application response
```

Suggested concepts:

```text
AssistantResponseRequest
AssistantResponse
TokenUsage
GenerateAssistantResponse
LanguageModelProvider
OpenAILanguageModelProvider
```

## Provider API

Use the OpenAI Responses API for the first provider adapter.

The adapter should accept a configured model and text input, create a response, extract output text and usage, and translate provider errors into application-level failures.

## Configuration

Secret:

```text
OPENAI_API_KEY
```

Non-secret:

```text
OPENAI_MODEL
```

Deliver `OPENAI_API_KEY` through the existing AWS Secrets Manager, Pod Identity, and Secrets Store CSI path.

The web UI and iPhone app must never receive the OpenAI key.

## Authorization

Add a capability-specific Auth0 permission:

```text
invoke:assistant
```

Do not overload backlog scopes.

## Initial scope

Included:

- one input string;
- one generated text response;
- request validation;
- provider-neutral application boundary;
- OpenAI adapter;
- controlled error mapping;
- behavior tests;
- deployment secret/config updates;
- fast-loop deployment and public smoke test.

Excluded:

- conversation persistence;
- streaming;
- RAG;
- embeddings;
- vector stores;
- tools or function calls;
- backlog mutation;
- prompt management UI;
- mobile voice input.

## Error behavior

Recommended public behavior:

```text
missing token                         → 401
valid token missing invoke scope      → 403
invalid request                       → 422 or project-standard 400
provider authentication failure      → controlled 502
provider timeout/unavailable          → controlled 503 or 504
successful generation                 → 200
```

Do not leak provider credentials, internal stack traces, or raw provider error bodies.

## Acceptance criteria

- `POST /api/v1/assistant/responses` accepts a non-empty `text` field.
- The route requires a valid bearer token.
- The route requires `invoke:assistant`.
- The route invokes an application use case rather than the OpenAI SDK directly.
- The application use case depends on a `LanguageModelProvider` port.
- The OpenAI implementation is isolated in a provider adapter.
- The OpenAI Responses API is used for text generation.
- The API response is normalized and does not expose the raw provider schema.
- `OPENAI_API_KEY` is read from AWS Secrets Manager through the existing mounted-secret path.
- `OPENAI_MODEL` is externally configurable and non-secret.
- Unit tests cover the use case with a fake provider.
- API behavior tests prove `401`, `403`, success, invalid input, and controlled provider failure.
- The complete test suite passes.
- The fast loop deploys the new image successfully.
- A public authenticated curl request returns generated text.

## Recommended implementation order

1. Review existing API route, auth dependency, configuration, error response, and test conventions.
2. Add provider-neutral request and response models.
3. Add `LanguageModelProvider`.
4. Add the application use case.
5. Add the OpenAI adapter and dependency.
6. Add configuration validation.
7. Add the authenticated route and scope.
8. Add behavior and unit tests.
9. Add `OPENAI_API_KEY` to AWS Secrets Manager and the runtime secret projection.
10. Add `OPENAI_MODEL` to Deployment configuration.
11. Deploy with the fast loop.
12. Run the acceptance curl tests.
13. Begin the minimal web UI story.

## Likely files needed

```text
pyproject.toml
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/api/routes.py
existing authentication/authorization modules
existing API error models and handlers
tests/behavior/
docs/deployment/eks/kubernetes/johnny-johnny-secret-provider-class.yml
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
scripts/fast-loop.sh
```
