# Assistant Response Endpoint Implementation Summary

**Date:** July 11, 2026
**Story:** `implement-assistant-response-endpoint`
**Status:** Repository implementation complete; Auth0/AWS/EKS acceptance operations pending

## Change Summary

Implemented one authenticated, provider-neutral assistant endpoint:

```http
POST /api/v1/assistant/responses
```

The route accepts a nonblank `text` value, requires `invoke:assistant`, calls the application-level `GenerateAssistantResponse` boundary, and returns normalized response text, model identity, response identity, and token usage.

The initial provider adapter uses the OpenAI Responses API. OpenAI SDK models and errors remain inside the adapter. The HTTP route and application use case expose only Johnny-Johnny contracts.

The implementation deliberately keeps retrieval, memory, tools, prompt assembly, and provider selection behind the use-case boundary so later RAG work does not require a new public endpoint.

## Files Affected

### Application and provider boundary

Created:

```text
src/johnny_johnny_agent/capabilities/assistant/__init__.py
src/johnny_johnny_agent/capabilities/assistant/models.py
src/johnny_johnny_agent/capabilities/assistant/provider.py
src/johnny_johnny_agent/capabilities/assistant/use_case.py
src/johnny_johnny_agent/providers/openai_language_model.py
```

Updated:

```text
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/api/app.py
src/johnny_johnny_agent/api/models.py
src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/api/security.py
src/johnny_johnny_agent/api/errors.py
pyproject.toml
uv.lock
```

### Tests

Created:

```text
tests/unit/test_assistant_response.py
tests/unit/test_openai_language_model.py
tests/unit/test_openai_configuration.py
```

Updated:

```text
tests/behavior/test_backlog_rest_api.py
```

### Runtime and deployment

Updated:

```text
.env.example
docs/deployment/eks/iam/johnny-johnny-secrets-policy.json
docs/deployment/eks/kubernetes/johnny-johnny-secret-provider-class.yml
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
scripts/fast-loop.sh
docs/architecture/EKS-DEPLOYMENT-FAST-LOOP.md
docs/deployment/eks-fast-testing-loop.md
docs/deployment/README.md
```

### Documentation

Created:

```text
docs/api/assistant-responses.md
docs/architecture/ASSISTANT-ENDPOINT-EXTENSIBILITY.md
docs/development/assistant-response-endpoint-implementation-summary-2026-07-11.md
```

Updated:

```text
README.md
docs/api/backlog-rest-api.md
docs/architecture/ASSISTANT-RESPONSE-ENDPOINT-STORY.md
```

## Imports Added, Removed, or Replaced

### Added

- OpenAI SDK imports: `openai`, `OpenAI`.
- Assistant application imports: `AssistantResponse`, `AssistantResponseRequest`, `TokenUsage`, `LanguageModelProvider`, `GenerateAssistantResponse`, and provider-neutral failures.
- FastAPI `Request` for application-state dependency resolution.
- Pydantic `field_validator` for nonblank assistant input.
- Dataclass `field` so `OpenAISettings.api_key` is excluded from object representations.
- `OpenAISettings` and `resolve_openai_settings` in application composition.

### Removed

- No existing functional imports were removed.

### Replaced

- The application factory description and route module description were broadened from backlog-only wording to Johnny-Johnny capability boundaries.
- The application factory's default composition now includes the OpenAI adapter behind `GenerateAssistantResponse` rather than constructing only the Auth0 boundary.

## Classes and Methods Added

### Provider-neutral models and port

```text
AssistantResponseRequest
AssistantResponse
TokenUsage
LanguageModelProvider.generate
```

### Application use case

```text
GenerateAssistantResponse.__init__
GenerateAssistantResponse.execute
```

### Provider-neutral failures

```text
LanguageModelProviderError
LanguageModelAuthenticationError
LanguageModelTimeoutError
LanguageModelUnavailableError
LanguageModelInvalidResponseError
```

### OpenAI adapter

```text
OpenAILanguageModelProvider.__init__
OpenAILanguageModelProvider.generate
_value
_optional_string
_required_string
_non_negative_int
```

### Configuration

```text
OpenAISettings
resolve_openai_settings
```

### HTTP contract and routing

```text
AssistantResponseRequest.require_non_blank_text
TokenUsageResponse
AssistantResponsePayload
assistant_response_generator
generate_assistant_response
```

### Error handlers

```text
_language_model_authentication_error
_language_model_timeout_error
_language_model_unavailable_error
_language_model_invalid_response_error
_language_model_provider_error
```

## Methods Replaced or Modified

- `create_app` now accepts an injectable `assistant_response_generator`, resolves required OpenAI settings for default composition, constructs `OpenAILanguageModelProvider`, and stores the use case in FastAPI application state.
- `install_exception_handlers` now registers provider-neutral assistant failures before the generic runtime handler.
- `ApiPermission` now includes `INVOKE_ASSISTANT`.
- `ERROR_RESPONSES` now documents assistant/provider `502`, `503`, and `504` outcomes.
- The fast loop now checks the assistant endpoint's unauthenticated `401` boundary and, when `ASSISTANT_ACCESS_TOKEN` is present, validates a normalized authenticated `200` response.

## Public Contract

Request:

```json
{
  "text": "What should we work on next?"
}
```

Response:

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

The raw OpenAI response is never returned.

## Authorization and Error Behavior

```text
missing/invalid bearer token       → 401
missing invoke:assistant           → 403
missing/blank/invalid request      → 422
provider credential rejection     → 502
provider malformed response       → 502
other controlled provider failure → 502
provider unavailable/rate limited → 503
provider timeout                   → 504
successful generation             → 200
```

Public provider errors use fixed messages and do not include provider response bodies, credentials, or stack traces.

## Configuration and Secret Boundary

Required API startup configuration:

```text
OPENAI_API_KEY  secret
OPENAI_MODEL    non-secret
```

`OpenAISettings.api_key` is excluded from `repr`. The EKS Deployment reads the key from the CSI-mounted Secrets Manager file. The model is regular Deployment environment configuration.

The IAM manifest grants read access to the `OPENAI_API_KEY-*` Secrets Manager ARN prefix. After the concrete secret exists, the policy can be narrowed to its exact ARN suffix if desired.

## Tests and Validation

Final local suite:

```text
137 passed, 1 skipped
```

The skipped test is the pre-existing live GitHub provider test.

Additional validation completed:

```text
uv lock --check
python -m compileall -q src tests
bash -n scripts/fast-loop.sh
JSON parse of the IAM policy
YAML parse of all EKS manifests
```

The tests prove:

- use-case delegation through a fake provider;
- trimming and blank-input rejection;
- OpenAI Responses API request shaping;
- output text, model, response ID, and usage normalization;
- mapping and object-shaped provider responses;
- malformed provider response rejection;
- SDK authentication, permission, timeout, connection, rate-limit, 4xx, and 5xx translation;
- missing OpenAI startup configuration fails closed;
- the API key is absent from `OpenAISettings` representations;
- endpoint `401`, `403`, `422`, `200`, `502`, `503`, and `504` behavior;
- provider details are not leaked through HTTP errors.

## External Acceptance Remaining

The repository archive contains no usable Git history or cloud-control credentials, so these environment mutations were not performed:

1. Add `invoke:assistant` to the Auth0 API and grant it to a smoke-test client or role.
2. Create or update the AWS Secrets Manager `OPENAI_API_KEY` secret.
3. Apply the updated IAM policy and Kubernetes manifests.
4. Supply `ASSISTANT_ACCESS_TOKEN` and run `scripts/fast-loop.sh`.
5. Confirm the public HTTPS endpoint returns normalized generated text.

These are deployment acceptance steps, not missing application code.
