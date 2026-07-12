# Johnny-Johnny Command Cheat Sheet

**Session:** Authenticated routing and semantic retrieval foundations  
**Date:** July 12, 2026  
**Timestamp:** 2026-07-12-182916

Sensitive values are represented with placeholders. Never paste access tokens, client secrets, or API keys into durable documentation.

## Git and Archive

### Check branch and working tree

```bash
git status --short --branch
```

Confirmed that development was on a clean `dev` branch at the beginning of the implementation.

### Create an optional feature branch

```bash
git switch -c feature/assistant-intent-routing
```

Suggested as an isolated branch, but not used because development continued directly on `dev`.

### Archive tracked project files

```bash
git archive   --format=zip   --output=../johnny-johnny-agent-$(date +%Y%m%d-%H%M%S).zip   HEAD
```

Creates a timestamped ZIP beside the repository containing only files tracked in the current commit.

### Inspect the archive

```bash
unzip -l ../johnny-johnny-agent-*.zip | head -80
```

Lists the first archive entries to verify its contents.

## File Inspection and Python Import Diagnostics

### Inspect the assistant route from the shell

```bash
sed -n '250,282p' src/johnny_johnny_agent/api/routes.py
```

Suggested before the IDE workflow was adopted.

### Verify new assistant contracts import

```bash
uv run python -c "from johnny_johnny_agent.capabilities.assistant.models import AssistantInvocationRequest, AssistantPrincipal; print('imports ok')"
```

Distinguished real Python import failures from IDE highlighting.

### Check the exact file Python reads

```bash
python -c "from pathlib import Path; p=Path('src/johnny_johnny_agent/capabilities/assistant/models.py'); print(p.resolve()); print('AssistantInvocationRequest present:', 'class AssistantInvocationRequest' in p.read_text())"
```

Revealed that the intended class was not in the on-disk assistant models file.

### Recheck class presence after saving the correct file

```bash
python -c "from pathlib import Path; p=Path('src/johnny_johnny_agent/capabilities/assistant/models.py'); print('AssistantInvocationRequest present:', 'class AssistantInvocationRequest' in p.read_text())"
```

Verified the correct module contents.

### Verify OpenAI language-model provider import

```bash
uv run python -c "from johnny_johnny_agent.providers.openai_language_model import OpenAILanguageModelProvider; print('provider import ok')"
```

Checked provider structure after a whole-file replacement.

## Focused Tests

### Assistant orchestration tests

```bash
uv run pytest tests/unit/test_assistant_response.py -v
```

Verified principal sanitization, model routing, general-chat behavior, backlog placeholder behavior, and invalid-route failure.

### OpenAI language-model adapter tests

```bash
uv run pytest tests/unit/test_openai_language_model.py -v
```

Verified provider request construction, including separate internal instructions.

### Retrieval-document tests

```bash
uv run pytest tests/unit/test_backlog_retrieval_documents.py -v
```

Verified epic and issue source text, parent-epic context, exclusions, SHA-256 hashing, and status-only stability.

### Embedding configuration tests

```bash
uv run pytest tests/unit/test_openai_embedding_configuration.py -v
```

Verified required environment settings, dimension validation, and secret-safe representation.

### OpenAI embedding adapter tests

```bash
uv run pytest tests/unit/test_openai_embeddings.py -v
```

Verified batched input, input order, dimensions, blank input, and malformed provider responses.

### PostgreSQL embedding repository tests

```bash
uv run pytest tests/unit/test_backlog_retrieval_postgres.py -v
```

Verified lookup parameters, vector serialization, upsert SQL, and missing-item handling without touching the real database.

### Embedding refresh tests

```bash
uv run pytest tests/unit/test_backlog_embedding_refresh.py -v
```

Verified created, unchanged, changed-source, and changed-model refresh decisions.

### Run the full suite

```bash
uv run pytest
```

Produced a `151 passed` checkpoint before the later embedding persistence work. This command must be rerun at the start of the next session after the final refresh changes.

## Local Server

### Start the API locally

```bash
uv run jj serve --host 127.0.0.1 --port 8000
```

Started the authenticated assistant API on loopback.

## Environment Loading

### Load `.env` into the current shell

```bash
set -a; source .env; set +a
```

Exports variables from `.env` for local commands.

### Set the Auth0 M2M client ID

```bash
export AUTH0_CLIENT_ID='<AUTH0_M2M_CLIENT_ID>'
```

Sets the non-secret client identifier.

### Read the Auth0 client secret without shell echo

```bash
read -s -p "Auth0 client secret: " AUTH0_CLIENT_SECRET; echo; export AUTH0_CLIENT_SECRET
```

Accepts the secret interactively without displaying it.

## Auth0 Token Retrieval

### Request a machine-to-machine access token

```bash
TOKEN_RESPONSE=$(
  curl --silent --show-error --fail-with-body     -X POST     "https://${AUTH0_DOMAIN}/oauth/token"     -H "Content-Type: application/json"     -d "{
      \"client_id\": \"${AUTH0_CLIENT_ID}\",
      \"client_secret\": \"${AUTH0_CLIENT_SECRET}\",
      \"audience\": \"${AUTH0_AUDIENCE}\",
      \"grant_type\": \"client_credentials\",
      \"scope\": \"invoke:assistant\"
    }"
)
```

Requests a short-lived token. Do not print `TOKEN_RESPONSE`.

### Extract the token without printing it

```bash
export ASSISTANT_ACCESS_TOKEN="$(
  printf '%s' "${TOKEN_RESPONSE}" |
    python -c 'import json, sys; print(json.load(sys.stdin)["access_token"])'
)"
```

Parses the token into an environment variable.

### Verify that the token exists

```bash
test -n "${ASSISTANT_ACCESS_TOKEN}" && echo "access token set"
```

Checks only that the token is non-empty.

## Authenticated Endpoint Smoke Tests

### General-chat route

```bash
curl --silent --show-error --fail-with-body   -X POST   http://127.0.0.1:8000/api/v1/assistant/responses   -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}"   -H "Content-Type: application/json"   -d '{
    "text": "What is the airspeed velocity of a laden swallow?",
    "model": "gpt-5.6"
  }'
```

Verified model classification as `general_chat` followed by normal assistant generation.

### Backlog route

```bash
curl --silent --show-error --fail-with-body   -X POST   http://127.0.0.1:8000/api/v1/assistant/responses   -H "Authorization: Bearer ${ASSISTANT_ACCESS_TOKEN}"   -H "Content-Type: application/json"   -d '{
    "text": "Put the webhook story into progress.",
    "model": "gpt-5.6"
  }'
```

Verified model classification as `backlog` and the deterministic safe placeholder.

## PostgreSQL and pgvector

### Find the pgvector extension schema

```sql
SELECT
    extname,
    nspname AS extension_schema
FROM pg_extension
JOIN pg_namespace
    ON pg_namespace.oid = pg_extension.extnamespace
WHERE extname = 'vector';
```

Confirmed that pgvector extension objects live in `public`.

### Apply the embedding-table migration with `psql`

```bash
psql "${DATABASE_URL}"   -v ON_ERROR_STOP=1   -f docs/database/postgres/003_create_backlog_item_embeddings.sql
```

Applies the migration from the shell. The migration was actually run through IntelliJ during this session.

### Verify that the table exists

```sql
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'johnny_johnny'
  AND table_name = 'backlog_item_embeddings';
```

Checks for the application table.

### Inspect embedding-table columns

```sql
SELECT
    column_name,
    data_type,
    udt_schema,
    udt_name,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'johnny_johnny'
  AND table_name = 'backlog_item_embeddings'
ORDER BY ordinal_position;
```

Verified that the `embedding` column uses the `public.vector` type.

## Real OpenAI Embedding Smoke Test

```bash
set -a; source .env; set +a

uv run python - <<'PY'
from johnny_johnny_agent.config import resolve_openai_embedding_settings
from johnny_johnny_agent.providers.openai_embeddings import OpenAIEmbeddingProvider

settings = resolve_openai_embedding_settings()
provider = OpenAIEmbeddingProvider(settings)

vector = provider.embed_texts(
    ("Implement GitHub webhook synchronization for provider-originated updates.",)
)[0]

print("model:", vector.model)
print("dimensions:", vector.dimensions)
print("actual length:", len(vector.values))
print("first five values:", vector.values[:5])
PY
```

Made one real embedding request and verified:

```text
model: text-embedding-3-small
dimensions: 1536
actual length: 1536
```

The vector was not persisted by this command.

## Configuration Snippets

These are configuration entries rather than shell commands, but they are included for the cookbook.

### Local `.env` and `.env.example`

```dotenv
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

### Kubernetes Deployment

```yaml
- name: OPENAI_EMBEDDING_MODEL
  value: "text-embedding-3-small"
- name: OPENAI_EMBEDDING_DIMENSIONS
  value: "1536"
```

These are non-secret runtime settings. `OPENAI_API_KEY` remains in AWS Secrets Manager.
