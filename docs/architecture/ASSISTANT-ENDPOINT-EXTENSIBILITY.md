# Assistant Endpoint Extensibility Guidance

**Project:** Johnny-Johnny Agent
**Purpose:** Preserve one stable assistant endpoint while adding RAG, memory, tools, and provider evolution behind it.

## Core Decision

The public endpoint should represent the **Johnny-Johnny assistant capability**, not a direct OpenAI completion or proxy.

Recommended route:

```http
POST /api/v1/assistant/responses
```

The route should call a broad application use case:

```text
GenerateAssistantResponse
```

Do not model the use case as something provider-specific such as:

```text
SendTextToOpenAI
```

This distinction is what allows the implementation to evolve without forcing the web UI or iPhone client to adopt a new endpoint.

## Evolution Path

### Initial implementation

```text
text
→ GenerateAssistantResponse
→ LanguageModelProvider
→ OpenAI provider adapter
→ normalized response
```

### Later RAG implementation

```text
text
→ determine intent
→ retrieve relevant knowledge
→ rank and assemble context
→ GenerateAssistantResponse
→ LanguageModelProvider
→ grounded response with sources
```

### Later memory and tools

```text
text
→ load conversation state
→ retrieve relevant context
→ select permitted tools
→ execute tools
→ assemble model input
→ LanguageModelProvider
→ normalized response
→ persist conversation state
```

The UI and iPhone app should continue calling the same public endpoint throughout these changes.

## Required Architectural Statement

Add this requirement to the implementation story:

> The endpoint is an assistant-orchestration boundary, not an OpenAI proxy. Retrieval, memory, tool execution, prompt construction, and provider selection may be added behind the application use case without changing the route.

Add this acceptance criterion:

> Future retrieval-augmented generation must be implementable behind `GenerateAssistantResponse` without requiring a new public endpoint or breaking the original request and response contract.

## Initial Request Contract

Keep the first request intentionally small:

```json
{
  "text": "What should we work on next?"
}
```

Later, optional fields can be added without breaking existing clients:

```json
{
  "text": "What should we work on next?",
  "conversation_id": "conversation-123",
  "context": {
    "project": "Johnny-Johnny Backlog Persistence Sandbox"
  }
}
```

Existing clients can continue sending only `text`.

## Initial Response Contract

Start with a normalized provider-neutral response:

```json
{
  "response_id": "response-123",
  "text": "The next priority is...",
  "model": "configured-model",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 60
  }
}
```

Later, optional grounding information can be added:

```json
{
  "response_id": "response-123",
  "text": "The next priority is...",
  "model": "configured-model",
  "usage": {
    "input_tokens": 900,
    "output_tokens": 60
  },
  "sources": [
    {
      "id": "design-canonical-backlog-persistence",
      "title": "Design Canonical Backlog Persistence",
      "type": "backlog_item"
    }
  ]
}
```

Old clients should be able to ignore new optional fields.

## Internal Extension Points

The initial use case may depend only on:

```text
LanguageModelProvider
```

Later, it can coordinate additional ports:

```text
GenerateAssistantResponse
├── KnowledgeRetriever
├── ConversationRepository
├── PromptAssembler
├── ToolExecutor
└── LanguageModelProvider
```

These collaborators should be introduced only when their capabilities are implemented. The first story should not build speculative RAG infrastructure.

## Provider Boundary

The route and application service must not expose the raw OpenAI response format.

The OpenAI adapter should translate provider-specific data into Johnny-Johnny models such as:

```text
AssistantResponseRequest
AssistantResponse
TokenUsage
SourceReference
```

This makes it possible to change models or providers later without changing the public API.

## What Can Stay Behind This Endpoint

The same endpoint can support:

- retrieval-augmented generation;
- source citations;
- conversation memory;
- prompt construction;
- model selection;
- provider switching;
- backlog-aware context;
- document retrieval;
- tool-assisted responses;
- permitted backlog actions;
- response metadata.

## Possible Future Transport Exceptions

A separate transport may eventually be appropriate for fundamentally different interaction modes, especially:

- token streaming through Server-Sent Events;
- real-time bidirectional voice through WebSockets;
- long-running asynchronous jobs.

Those transport additions do not invalidate the stable assistant capability. Ordinary request/response RAG should remain behind:

```http
POST /api/v1/assistant/responses
```

## Guiding Principle

```text
Keep the public assistant contract stable.
Evolve orchestration, retrieval, memory, tools, and providers behind it.
```
