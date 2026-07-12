# Authenticated UI Companion Change Summary

**Date:** July 11, 2026  
**Capability:** Authenticated Johnny-Johnny browser access  
**Status:** Implemented; environment deployment pending

## Purpose

Support the authenticated Johnny-Johnny UI without exposing arbitrary provider configuration or allowing the browser to own assistant orchestration. The agent remains the provider-neutral resource server and the canonical backlog boundary.

## Behavior added

- Authenticated clients can retrieve the server-owned assistant model catalog through `GET /api/v1/assistant/models`.
- `POST /api/v1/assistant/responses` accepts an optional model identifier.
- A requested model must be present in the server's configured allow-list.
- The configured default model remains the fallback and is always included in the catalog.
- Unsupported model requests return HTTP `422` with error code `assistant_model_not_available` and the available identifiers.
- Existing text-only requests remain compatible.
- Both assistant endpoints require `invoke:assistant`.

## Boundary changes

### Domain and application

- Added `AssistantModel` as a provider-neutral catalog item.
- Added optional `model` to `AssistantResponseRequest`.
- Added `LanguageModelProvider.available_models()` to the provider port.
- Added `GenerateAssistantResponse.available_models()` to expose the catalog through the application boundary.
- Added `UnsupportedLanguageModelError` as a controlled, provider-neutral failure.

### OpenAI adapter and configuration

- Added optional comma-separated `OPENAI_MODELS` configuration.
- Normalized the allow-list so `OPENAI_MODEL` is first, always allowed, and de-duplicated.
- Validated model selection before the OpenAI Responses API call.
- Passed the selected model through the provider adapter while preserving normalized response output.

### API

- Added model-catalog response models and the authenticated catalog route.
- Extended assistant request validation for an optional non-blank model.
- Added controlled unsupported-model error mapping.

### Deployment

- Added `OPENAI_MODELS` to the EKS Deployment as non-secret configuration.
- Updated the canonical Ingress to route `/api/v1` to the agent and `/` to the separate UI Service under the existing ALB and ACM certificate.

## Files changed

```text
.env.example
README.md
docs/api/assistant-responses.md
docs/api/backlog-rest-api.md
docs/deployment/README.md
docs/deployment/eks/kubernetes/johnny-johnny-agent-deployment.yml
docs/deployment/eks/kubernetes/johnny-johnny-ingress.yml
src/johnny_johnny_agent/api/errors.py
src/johnny_johnny_agent/api/models.py
src/johnny_johnny_agent/api/routes.py
src/johnny_johnny_agent/capabilities/assistant/__init__.py
src/johnny_johnny_agent/capabilities/assistant/models.py
src/johnny_johnny_agent/capabilities/assistant/provider.py
src/johnny_johnny_agent/capabilities/assistant/use_case.py
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/providers/openai_language_model.py
tests/behavior/test_backlog_rest_api.py
tests/unit/test_assistant_response.py
tests/unit/test_openai_configuration.py
tests/unit/test_openai_language_model.py
```

## Verification

- Python source and tests compiled successfully.
- `147 passed, 1 skipped` with the available system Python.
- The environment could not install the locked OpenAI dependency, so a temporary import-compatible exception stub was used only for this local test run. It is not part of the repository or delivery archive.
- Kubernetes YAML parsed successfully and the shared Ingress matches the UI copy.

## Outstanding acceptance

- Configure the Auth0 Single Page Application used by the browser.
- Build and push the UI image.
- Apply the shared Ingress and UI workload to EKS.
- Complete an interactive user login, model-catalog, assistant-generation, document, and Git projection acceptance pass over the public HTTPS origin.
