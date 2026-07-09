# Working Agreement

Version: 1.0  
Last Updated: July 9, 2026

## Purpose

This document defines how contributors collaborate while developing Johnny-Johnny.

See `ENGINEERING_PRINCIPLES.md` for software design principles.

## Collaboration

- Discuss design before coding.
- Finish one story at a time.
- Prefer small, coherent changes.
- Challenge ideas respectfully and explain tradeoffs.
- Architectural consistency is more important than personal preference.

## Code Changes

Every implementation should include:

- Change Summary
- Files affected
- Imports added, removed, or replaced
- Methods added
- Methods replaced

Prefer complete method or function replacements over partial edits.

## Session Workflow

Session handoffs should contain:

- Current story
- Decisions made
- Outstanding work
- Relevant project structure
- Files likely to be needed

Do not duplicate long-lived guidance already captured in this document.

## Engineering Session Closure

An engineering session is the unit of work. It is independent of elapsed time and independent of chat conversations or browser tabs.

When the user says:

```text
Let's wrap the session.
```

or requests a session handoff, the assistant should perform the Engineering Session Closure process.

### Engineering Session Closure

1. Review the work completed during the session.
2. Determine which long-lived engineering artifacts should be created or updated.
3. Generate or update those engineering artifacts.
4. Generate the session index.

Potential artifacts include:

- Backlog updates
- ADRs
- Engineering Principles
- Working Agreement
- AI Collaboration documentation
- Specifications
- Behavior tests
- Design documents
- Other project documentation

The objective is to convert ephemeral conversation into durable engineering knowledge.

### Session Index

After all required engineering artifacts have been generated or updated, generate a downloadable `session-index.md`.

The session index is **not** a duplicate of the documentation created during the session. It is a navigation document that records:

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

#### Session Metadata

The session index should begin with a metadata section that captures the current engineering context.

The metadata section should include:

- Date
- Project Version (if known)
- Git Branch
- Current Story
- Next Story (if known)

Example:

```markdown
# Session Index

**Date:** July 9, 2026

**Project Version:** 0.7.0

**Git Branch:** dev

**Current Story:** move-issue-command

**Next Story:** expand-move-behavior-tests
```

The Git branch should always reflect the branch currently being used for development at the time the session index is generated.

The purpose of `session-index.md` is to allow a future engineering session to begin immediately without depending on previous conversation history.

### Guiding Principle

The objective is to minimize context loss between sessions.

Every engineering session should conclude with sufficient documentation that neither the human nor the AI must rely on memory to resume productive work.

## Living Document

This agreement is expected to evolve over time.