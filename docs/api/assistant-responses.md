# Assistant Responses API

**Status:** Implemented; deployment of the model-catalog revision remains an environment operation  
**Base path:** `/api/v1`  
**Endpoints:** `GET /api/v1/assistant/models`, `POST /api/v1/assistant/responses`

## Purpose

The endpoints expose the Johnny-Johnny assistant capability to authenticated clients without exposing an OpenAI credential or provider-specific response schema.

They are an assistant-orchestration boundary, not an OpenAI proxy:

```text
HTTP route
→ GenerateAssistantResponse
→ LanguageModelProvider
→ OpenAILanguageModelProvider
→ normalized Johnny-Johnny response
```

Retrieval, memory, tools, prompt construction, and provider evolution may be added behind `GenerateAssistantResponse` without changing the response route.

## Authorization

Both endpoints require a valid Auth0 bearer token with:

```text
invoke:assistant
```

Backlog scopes do not grant assistant access, and `invoke:assistant` does not grant backlog access.

## Model catalog

```http
GET /api/v1/assistant/models
Authorization: Bearer ACCESS_TOKEN
```

```json
{
  "default_model": "gpt-5.6",
  "models": [
    {
      "id": "gpt-5.6",
      "label": "gpt-5.6",
      "is_default": true
    }
  ]
}
```

The catalog is provider-neutral and generated from server configuration. It does not disclose provider credentials or allow the client to name an arbitrary model.

## Generation request

```http
POST /api/v1/assistant/responses
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

```json
{
  "text": "What should we work on next?",
  "model": "gpt-5.6"
}
```

`text` is required and must contain at least one non-whitespace character. `model` is optional; omission selects the configured default. When supplied, it must equal an identifier returned by the model catalog. Unknown request fields are rejected.

## Response

```json
{
  "response_id": "resp_123",
  "text": "The next priority is...",
  "model": "gpt-5.6",
  "usage": {
    "input_tokens": 18,
    "output_tokens": 9
  }
}
```

The contract is provider-neutral. The API does not return the raw OpenAI response object.

## Provider behavior

The initial adapter uses the OpenAI Responses API. It validates model selection against the server-owned allow-list before invoking the SDK, passes one text input, disables response storage for this request, reads the SDK's aggregated output text, and translates response metadata into Johnny-Johnny models.

Provider-specific SDK exceptions are translated before they cross the application boundary.

## Runtime configuration

```env
OPENAI_API_KEY=server-owned-secret
OPENAI_MODEL=gpt-5.6
OPENAI_MODELS=gpt-5.6
```

`OPENAI_API_KEY` and `OPENAI_MODEL` are required at API startup. `OPENAI_MODELS` is optional comma-separated non-secret configuration. The default model is always inserted first and remains the fallback, even when it is omitted from the explicit allow-list.

In EKS, the key is mounted from AWS Secrets Manager through the existing Pod Identity and Secrets Store CSI path. Model configuration remains in the Deployment and can change without changing the public API.

## Error contract

| HTTP status | Stable code | Meaning |
|---|---|---|
| `401` | `authentication_required` or `invalid_access_token` | No trusted bearer token |
| `403` | `insufficient_scope` | Token lacks `invoke:assistant` |
| `422` | `request_validation_error` | Missing, blank, or otherwise invalid request |
| `422` | `assistant_model_not_available` | Requested model is outside the server allow-list |
| `502` | `assistant_provider_authentication_failed` | Server-owned provider credential rejected |
| `502` | `assistant_provider_invalid_response` | Provider data cannot satisfy the public contract |
| `502` | `assistant_provider_failed` | Other controlled provider rejection |
| `503` | `assistant_provider_unavailable` | Provider connection, rate limit, configuration, or server availability failure |
| `504` | `assistant_provider_timeout` | Provider request timed out |

Provider credentials, raw provider bodies, and stack traces are not returned.

## Curl exercise

```bash
export API='http://127.0.0.1:8000/api/v1'
: "${ASSISTANT_ACCESS_TOKEN:?Obtain a token with invoke:assistant}"

curl -fsS \
  -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}" \
  "${API}/assistant/models" \
  | python3 -m json.tool

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary '{"text":"What should we work on next?","model":"gpt-5.6"}' \
  "${API}/assistant/responses" \
  | python3 -m json.tool
```

## Extension contract

Future retrieval-augmented generation must be implementable behind `GenerateAssistantResponse` without requiring a new public response endpoint or breaking the original request and response contract. Optional fields such as `conversation_id`, `context`, and `sources` may be added compatibly when those capabilities are implemented.

Streaming, bidirectional voice, or long-running asynchronous jobs may eventually require additional transports, but ordinary request/response assistant orchestration remains behind this endpoint.

## Test coverage

- use-case catalog delegation, request normalization, and blank-input rejection;
- model allow-list normalization and default insertion;
- OpenAI Responses API request shaping for default and selected models;
- rejection of unconfigured models before any provider call;
- malformed provider response handling;
- OpenAI SDK authentication, timeout, connection, rate-limit, and status failure translation;
- model-catalog and generation endpoint authorization;
- endpoint `401`, `403`, `422`, `200`, `502`, `503`, and `504` behavior;
- proof that controlled error responses do not leak provider details.
