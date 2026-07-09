# Engineering Session Closure

## Core Idea

The goal of an engineering session is to convert ephemeral conversation into durable engineering knowledge.

A conversation is temporary.

Engineering artifacts are durable.

The session index is the bridge between them.

---

## Engineering Session

An engineering session is the unit of work.

It is not defined by elapsed time, a single chat conversation, or a browser tab. A session may last ten minutes, several hours, or span multiple conversations.

What matters is the engineering context being advanced.

---

## Why This Matters

AI assistants do not experience continuity the way humans do.

A future session may not have access to the reasoning, discussion, alternatives, or decisions that occurred in a previous conversation.

Because of that, important knowledge must be promoted out of the conversation and into durable artifacts.

Examples include:

- Code
- Tests
- ADRs
- Backlog stories
- Working agreements
- Engineering principles
- Specifications
- Design notes
- AI collaboration documentation

The purpose is not to summarize everything that was said.

The purpose is to preserve the engineering knowledge that should survive the conversation.

---

## Session Closure

At the end of an engineering session, or before moving to a new conversation, the session should be closed deliberately.

Session closure should answer:

> What durable knowledge was created or changed during this session?

That question determines which artifacts need to be created or updated.

---

## Artifact First, Index Last

The session index should be generated only after durable artifacts have been created or updated.

The index is not the documentation itself.

It is a navigation document that points to the durable knowledge produced by the session.

For example:

```text
Conversation
    ↓
Engineering Decisions
    ↓
Durable Artifacts
    ↓
session-index.md
```

The session index should describe what changed, where the durable artifacts live, what remains unfinished, and what the next session should do first.

---

## Session Index

A `session-index.md` should include:

- Session summary
- Stories completed
- Current story
- Engineering artifacts created or updated
- Files changed
- Lessons learned
- Bugs found and resolved
- Outstanding work
- Next recommended step
- Files likely needed next
- Immediate first task

The goal is that a future session can begin immediately by reading the session index and the referenced artifacts.

---

## Guiding Principle

Do not rely on memory when an engineering artifact should exist.

If the session produced architectural knowledge, create or update an ADR.

If the session changed collaboration practice, update the Working Agreement or AI Collaboration documentation.

If the session changed expected behavior, create or update tests.

If the session completed work, update the backlog.

If the session left work unfinished, record the next step in `session-index.md`.

---

## Emerging Hypothesis

Effective AI collaboration is not primarily about preserving chat history.

It is about continuously refining conversation into durable project knowledge.

The better the durable artifacts become, the less important the raw conversation becomes.