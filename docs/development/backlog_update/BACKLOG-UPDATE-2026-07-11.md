# Backlog Update — July 11, 2026

## Completed

### `implement-assistant-response-endpoint`

**Recommended status:** Done

Completion evidence:

- provider-neutral assistant use case and language-model port implemented;
- OpenAI Responses API adapter implemented;
- `POST /api/v1/assistant/responses` implemented;
- dedicated `invoke:assistant` permission implemented and configured in Auth0;
- AWS runtime IAM policy updated for `OPENAI_API_KEY`;
- EKS deployment completed through `scripts/fast-loop.sh`;
- full canonical-repository test suite passed with `138 passed`;
- public authenticated generation returned `200`;
- normalized response contained response ID, generated text, model, and token usage.

Durable acceptance evidence is recorded in:

```text
docs/development/assistant-response-endpoint-deployment-acceptance-2026-07-11.md
```

## Next Recommended Story

Suggested ID:

```text
update-johnny-johnny-ui-for-authenticated-agent-access
```

Working title:

```text
Update Johnny-Johnny UI for Authenticated Agent Access
```

Initial intent:

- update the existing `johnny-johnny-ui`;
- authenticate browser users through Auth0;
- use Authorization Code Flow with PKCE;
- request the Johnny-Johnny API audience;
- exercise the deployed agent backend;
- add an initial stateless chat window for the assistant endpoint;
- preserve backend ownership of prompt assembly and future conversation orchestration.

Detailed UX requirements and acceptance criteria are intentionally deferred until the user supplies UI guidelines in the next session.

## Deferred Capability Work

The following remain later stories behind the stable assistant boundary:

- conversation persistence;
- optional `conversation_id`;
- RAG and source references;
- memory;
- prompt assembly;
- tool execution;
- model/provider selection;
- streaming;
- native iPhone voice controller.

## Optional Operational Follow-up

- Confirm the completed commit is present on `origin/dev`.
- Consider narrowing the IAM resource from `OPENAI_API_KEY-*` to the exact generated secret ARN.
- Decide whether the fast loop should always require an authenticated assistant token in CI-like environments or continue treating it as optional for local/operator runs.
