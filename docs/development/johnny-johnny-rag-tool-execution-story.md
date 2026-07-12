# Johnny-Johnny RAG and Tool-Execution Learning Story

**Status:** Planned  
**Sequence:** Begin immediately after the native iPhone assistant app is complete  
**Implementation Style:** Guided, hands-on learning session  
**Primary Technologies:** PostgreSQL, pgvector, LangChain, LangGraph, OpenAI embeddings and language models

## Purpose

Build the first Johnny-Johnny workflow that uses retrieval-augmented generation and a safe application tool from chat.

The story is intentionally designed as a learning exercise. The assistant should guide Grant through each small implementation step, explain the concepts and tradeoffs, and have Grant make and run the changes rather than delivering a completed generated implementation.

The first workflow will allow an authenticated user to describe a backlog item in natural language, have Johnny-Johnny retrieve the likely canonical story using vector similarity, propose a status update and optional comment, require explicit confirmation, and execute the change through the existing canonical backlog mutation and GitHub synchronization path.

## Learning Objectives

The story should provide hands-on experience with:

- retrieval-augmented generation;
- document modeling for retrieval;
- embeddings;
- vector storage with pgvector;
- semantic similarity search;
- grounding model output in canonical application data;
- LangChain model, document, retriever, structured-output, and tool abstractions;
- LangGraph state, nodes, transitions, persistence, and human-in-the-loop interruption;
- safe tool execution;
- explicit confirmation before mutation;
- evaluation of retrieval quality and hallucination resistance;
- preserving domain and provider boundaries while introducing AI orchestration.

## Architectural Principle

RAG, tool definitions, model reasoning, application validation, and mutation execution are separate responsibilities.

```text
Tool registry
→ defines what Johnny-Johnny is allowed to do

RAG
→ retrieves relevant Johnny-Johnny project knowledge

Language model
→ interprets the user request using the retrieved context and available tools

Application layer
→ validates authorization, identifiers, status values, and confirmation

Existing mutation capability
→ updates canonical PostgreSQL state and synchronizes the GitHub projection
```

The language model must never update GitHub directly and must never bypass the canonical backlog application capability.

## Initial User Experience

A user should be able to say something like:

> Put the story about automatically receiving GitHub updates into progress and add a comment saying we are starting the first AI mutation experiment.

Johnny-Johnny should:

1. retrieve likely backlog items semantically;
2. identify the strongest grounded candidate;
3. reload the current canonical record from PostgreSQL;
4. explain what it found;
5. show the proposed status and comment mutation;
6. pause for explicit confirmation;
7. execute through the existing backlog mutation use case;
8. synchronize the required GitHub projection;
9. report success or a clear consistency failure.

An example preview:

```text
I found “Implement GitHub Webhook Synchronization.”

Proposed change:
Status: Ready → In Progress
Comment: “Starting the first AI-driven backlog mutation experiment.”

Confirm this update?
```

## First Supported Tool

The first version should expose one deliberately narrow mutation tool.

### Supported behavior

- update one existing backlog item;
- change its status;
- optionally append one comment;
- require explicit confirmation;
- execute through the existing Johnny-Johnny backlog mutation capability;
- preserve canonical PostgreSQL state and required GitHub synchronization behavior.

### Initially excluded

- creating stories;
- deleting stories;
- moving stories between epics;
- changing titles;
- rewriting descriptions;
- replacing acceptance criteria;
- purging projects;
- broad reconciliation commands;
- arbitrary shell or CLI command execution.

## Retrieval Scope

The first version will use pgvector, which is already installed and available in the Johnny-Johnny PostgreSQL environment.

Each backlog item will initially be represented as one retrievable document containing selected canonical information such as:

```text
Title
Canonical ID
Epic title or canonical epic ID
Current status
Description
Acceptance criteria
Selected recent comments
```

A representative retrieval document might look like:

```text
Title: Implement GitHub Webhook Synchronization
Canonical ID: implement-github-webhook-synchronization
Epic: Backlog-as-Code Synchronization
Status: Ready
Description: Receive and validate GitHub webhook events...
Acceptance criteria: ...
Recent comments: ...
```

The vector record metadata should contain stable application identifiers rather than provider-specific identifiers.

Example metadata:

```json
{
  "backlog_item_id": "database-uuid",
  "canonical_id": "implement-github-webhook-synchronization",
  "project_id": "database-project-uuid",
  "document_type": "backlog_item"
}
```

The embedding is only a retrieval aid. It is never canonical state.

After a vector search returns a candidate, Johnny-Johnny must reload the current backlog item from the canonical tables before proposing or executing a mutation.

```text
Vector result
→ stable canonical identifier
→ reload current canonical record
→ validate
→ propose mutation
```

## Proposed Embedding Persistence

The exact schema should be designed during the guided implementation, but the first version will likely introduce a table conceptually similar to:

```sql
CREATE TABLE backlog_item_embeddings (
    backlog_item_id uuid PRIMARY KEY
        REFERENCES backlog_items(id) ON DELETE CASCADE,
    source_text text NOT NULL,
    source_hash text NOT NULL,
    embedding vector(<model-dimension>) NOT NULL,
    embedded_at timestamptz NOT NULL DEFAULT now()
);
```

The final vector dimension will be selected based on the chosen embedding model.

`source_hash` should allow Johnny-Johnny to detect when the retrieval document changed and needs to be re-embedded.

## Embedding Refresh Behavior

The first implementation should make refresh behavior explicit rather than magical.

At minimum, it should support:

- generating embeddings for existing backlog items;
- updating an embedding when its source text changes;
- avoiding unnecessary re-embedding when the source hash is unchanged;
- deleting vector records when canonical backlog items are deleted;
- reporting embedding failures clearly.

Automatic event-driven refresh can come later. A controlled CLI or application command is acceptable for the first learning version.

## LangChain Responsibilities

LangChain should be used for visible, focused building blocks rather than wrapping the whole application in an opaque agent.

Expected uses include:

- embedding-model integration;
- language-model integration;
- `Document` representations and metadata;
- a pgvector-backed retriever;
- prompt and message construction;
- structured model output;
- safe tool definition;
- tool argument schemas.

The implementation should make it clear which parts are LangChain abstractions and which parts remain Johnny-Johnny domain and application code.

## LangGraph Responsibilities

LangGraph should model the workflow explicitly.

A likely first graph:

```text
receive_request
→ retrieve_backlog_candidates
→ load_canonical_candidates
→ interpret_requested_action
→ resolve_or_request_disambiguation
→ prepare_mutation
→ interrupt_for_confirmation
→ execute_confirmed_mutation
→ render_result
```

The graph state should make important data visible and testable, such as:

- authenticated subject and permissions;
- original user message;
- retrieved vector candidates;
- canonical candidate records;
- resolved canonical backlog item;
- proposed status;
- proposed comment;
- confidence or ambiguity state;
- confirmation state;
- execution result;
- consistency or provider synchronization error.

The graph must pause before mutation and resume only after explicit confirmation.

## Ambiguity and Grounding Requirements

Johnny-Johnny must not invent canonical IDs or pretend to find a story when retrieval is weak.

Expected behavior:

- one strong candidate: show a grounded proposal;
- several plausible candidates: ask the user to choose;
- no grounded candidate: say that no reliable match was found;
- invalid requested status: reject or ask for correction;
- unauthorized user: do not expose or execute the tool;
- changed or deleted item between retrieval and execution: reload and fail safely;
- GitHub synchronization failure: report the explicit cross-boundary consistency outcome.

The first tests should deliberately include vague and ambiguous requests.

## Tool Contract

The backend owns the tool registry. The browser and model do not invent tools.

A conceptual tool proposal may resemble:

```json
{
  "tool": "update_backlog_item",
  "arguments": {
    "canonical_id": "implement-github-webhook-synchronization",
    "status": "In Progress",
    "comment": "Starting the first AI-driven backlog mutation experiment."
  }
}
```

This is only a proposal until:

- the canonical item exists;
- the authenticated user is authorized;
- the status is valid;
- the mutation is supported;
- the user has explicitly confirmed;
- the application use case accepts the operation.

## Security and Authorization

The workflow must remain behind the existing OAuth-protected Johnny-Johnny API.

Requirements:

- use the authenticated user identity and permissions from the validated access token;
- expose mutation tools only to authorized users;
- do not treat the model output as authorization;
- do not place secrets in prompts or tool arguments;
- require explicit confirmation for the mutation;
- preserve existing API error normalization;
- retain an auditable record of the requested and executed mutation where practical.

## Existing Capabilities to Reuse

The story should reuse the working Johnny-Johnny backbone:

- canonical PostgreSQL backlog state;
- stable canonical IDs;
- backlog read capabilities;
- targeted backlog mutation use cases;
- GitHub provider synchronization;
- authenticated assistant endpoint;
- model catalog and server-controlled model selection;
- web and native client surfaces;
- existing explicit cross-boundary consistency rules.

No duplicate chat-specific mutation implementation should be created.

## Guided Implementation Sequence

The story should be built in small, testable checkpoints.

1. Inspect the existing assistant use case and backlog mutation capability.
2. Verify pgvector in the development database.
3. Choose the first embedding model and vector dimension.
4. Design the backlog retrieval document format.
5. Design and create the embedding persistence table.
6. Generate one embedding manually.
7. Store and similarity-query the embedding directly in PostgreSQL.
8. Add deterministic source hashing and refresh behavior.
9. Create a controlled command or use case to embed existing backlog items.
10. Wrap vector search in a LangChain retriever.
11. Define structured candidate and proposed-mutation models.
12. Define the narrow safe backlog-update tool.
13. Introduce a minimal LangGraph state without changing existing assistant behavior.
14. Add retrieval and canonical-record loading nodes.
15. Add action interpretation and ambiguity handling.
16. Add the confirmation interrupt.
17. Add confirmed execution through the existing mutation use case.
18. Add result rendering and normalized failures.
19. Connect the graph to the assistant endpoint.
20. Exercise the workflow through the web chat and native iPhone client.
21. Evaluate lexical and semantic queries against known backlog items.
22. Document lessons, retrieval limitations, and next improvements.

## Testing Expectations

Tests should cover:

- retrieval document creation;
- source hashing;
- embedding persistence and refresh;
- vector similarity lookup;
- metadata-to-canonical-record resolution;
- strong-match behavior;
- ambiguous-match behavior;
- no-match behavior;
- invalid status rejection;
- unauthorized access;
- confirmation interruption;
- cancellation;
- successful mutation;
- GitHub synchronization failure handling;
- stale or deleted canonical records;
- model output that references nonexistent tools or identifiers;
- end-to-end authenticated API behavior.

The story should include a small evaluation set of natural-language requests with expected canonical matches.

Example prompts:

```text
Put the webhook story into progress.

Move the thing that automatically receives GitHub changes to In Progress.

Add a note to the OAuth UI story saying the first deployed login worked.

Start the provider synchronization story.
```

## Acceptance Criteria

The story is complete when:

- backlog items can be embedded and stored in pgvector;
- changed retrieval documents can be detected and re-embedded;
- a natural-language chat request can retrieve semantically relevant backlog items;
- vector results are resolved back to current canonical PostgreSQL records;
- Johnny-Johnny can propose a status update and optional comment for one grounded item;
- ambiguous or weak matches do not silently execute;
- the workflow pauses for explicit user confirmation;
- cancellation makes no mutation;
- confirmation executes through the existing backlog mutation capability;
- required GitHub synchronization occurs through the existing provider path;
- the final response clearly reports success or partial-failure consistency state;
- the workflow is orchestrated in LangGraph;
- LangChain is used for embeddings, retrieval, structured model interaction, and tool definition;
- behavior is covered by focused tests and at least one authenticated end-to-end demonstration;
- Grant can explain the roles of embeddings, vector search, retrieval, augmentation, model reasoning, tools, confirmation, and execution.

## Explicit Non-Goals for the First Version

- general autonomous agent behavior;
- unrestricted tool execution;
- shell-command generation and execution;
- multiple simultaneous backlog mutations;
- background GitHub webhook ingestion;
- full project-document RAG across every ADR and source file;
- long-term conversation memory;
- automatic execution without confirmation;
- replacing the canonical backlog domain or persistence model;
- allowing the model to communicate directly with GitHub.

## Likely Follow-On Work

After the first version is proven, possible extensions include:

- retrieve ADRs, decisions, and engineering documentation;
- use hybrid lexical and vector retrieval;
- add reranking;
- add embedding refresh through durable events;
- support more backlog tools;
- add native confirmation cards to the iPhone app;
- persist graph checkpoints and conversation threads;
- introduce server-side conversation memory;
- add GitHub webhook synchronization for provider-originated changes;
- evaluate alternative embedding models and chunking strategies;
- add retrieval observability, citations, and source displays.

## Working Agreement for This Story

This is a teaching story.

The assistant should:

- explain one concept at a time;
- inspect the existing implementation before proposing a change;
- provide focused complete function or method replacements when editing code;
- ask Grant to run each meaningful command and inspect the result;
- avoid delivering a complete generated application archive;
- preserve durable design decisions in project artifacts;
- create coherent commits at proven checkpoints;
- compare expected and actual retrieval behavior throughout the implementation.
