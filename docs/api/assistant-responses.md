# Assistant Responses API

**Status:** Implemented locally; deployment and live acceptance smoke remain
**Base path:** `/api/v1`
**Endpoint:** `POST /api/v1/assistant/responses`

## Purpose

The endpoint exposes the Johnny-Johnny assistant capability to authenticated clients without exposing an OpenAI credential or provider-specific response schema.

It is an assistant-orchestration boundary, not an OpenAI proxy:

```text
HTTP route
→ GenerateAssistantResponse
→ LanguageModelProvider
→ OpenAILanguageModelProvider
→ normalized Johnny-Johnny response
```

Retrieval, memory, tools, prompt construction, and provider selection may be added behind `GenerateAssistantResponse` without changing the route.

## Authorization

Requests require a valid Auth0 bearer token with:

```text
invoke:assistant
```

Backlog scopes do not grant assistant access, and `invoke:assistant` does not grant backlog access.

## Request

```http
POST /api/v1/assistant/responses
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

```json
{
  "text": "What should we work on next?"
}
```

`text` is required and must contain at least one non-whitespace character. Unknown request fields are rejected.

## Response

```json
{
  "response_id": "resp_123",
  "text": "The next priority is...",
  "model": "configured-or-returned-model",
  "usage": {
    "input_tokens": 18,
    "output_tokens": 9
  }
}
```

The contract is provider-neutral. The API does not return the raw OpenAI response object.

## Provider behavior

The initial adapter uses the OpenAI Responses API with the externally configured model. It passes one text input, disables response storage for this request, reads the SDK's aggregated output text, and translates response metadata into Johnny-Johnny models.

Provider-specific SDK exceptions are translated before they cross the application boundary.

## Runtime configuration

```env
OPENAI_API_KEY=server-owned-secret
OPENAI_MODEL=gpt-5.6
```

`OPENAI_API_KEY` is required at API startup and must remain server-side. In EKS it is mounted from AWS Secrets Manager through the existing Pod Identity and Secrets Store CSI path. `OPENAI_MODEL` is required, non-secret configuration and can be changed without changing the public API.

## Error contract

| HTTP status | Stable code | Meaning |
|---|---|---|
| `401` | `authentication_required` or `invalid_access_token` | No trusted bearer token |
| `403` | `insufficient_scope` | Token lacks `invoke:assistant` |
| `422` | `request_validation_error` | Missing, blank, or otherwise invalid request |
| `502` | `assistant_provider_authentication_failed` | Server-owned provider credential rejected |
| `502` | `assistant_provider_invalid_response` | Provider data cannot satisfy the public contract |
| `502` | `assistant_provider_failed` | Other controlled provider rejection |
| `503` | `assistant_provider_unavailable` | Provider connection, rate limit, or server availability failure |
| `504` | `assistant_provider_timeout` | Provider request timed out |

Provider credentials, raw provider bodies, and stack traces are not returned.

## Curl exercise

```bash
export API='http://127.0.0.1:8000/api/v1'
: "${ASSISTANT_ACCESS_TOKEN:?Obtain a token with invoke:assistant}"

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary '{"text":"What should we work on next?"}' \
  "${API}/assistant/responses" \
  | python3 -m json.tool
```

## Extension contract

Future retrieval-augmented generation must be implementable behind `GenerateAssistantResponse` without requiring a new public endpoint or breaking the original request and response contract. Optional fields such as `conversation_id`, `context`, and `sources` may be added compatibly when those capabilities are implemented.

Streaming, bidirectional voice, or long-running asynchronous jobs may eventually require additional transports, but ordinary request/response assistant orchestration remains behind this endpoint.

## Test coverage

- use-case delegation and blank-input rejection with a fake provider;
- OpenAI Responses API request shaping and normalized output;
- malformed provider response handling;
- OpenAI SDK authentication, timeout, connection, rate-limit, and status failure translation;
- endpoint `401`, `403`, `422`, `200`, `502`, `503`, and `504` behavior;
- proof that controlled error responses do not leak provider details.
