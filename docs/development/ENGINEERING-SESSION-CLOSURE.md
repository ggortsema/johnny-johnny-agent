# Engineering Session Closure

Please perform the complete Engineering Session Closure process described in the Working Agreement.

## 1. Review the Session

Review the work completed during this engineering session.

Identify:

- Architectural decisions
- Domain model changes
- New engineering principles
- Workflow/process improvements
- Specifications
- Database design decisions
- Testing strategy changes
- Documentation updates
- Backlog changes
- Bugs discovered
- Lessons learned

## 2. Promote Durable Knowledge

Determine which long-lived engineering artifacts should be created or updated.

Review each of the following categories.

If changes are required, create or update the artifact.

If no changes are required, explicitly state that the category was reviewed and no updates were necessary.

### Categories

- ADRs
- Architecture documentation
- Specifications
- Database documentation
- Engineering Principles
- Working Agreement
- AI Collaboration documentation
- Behavior tests
- Backlog
- Other project documentation

Do not rely on conversation history when durable documentation should exist.

## 3. Verify Completeness

Before generating the session index, verify that every important decision made during the session has been captured in an appropriate engineering artifact.

If something exists only in conversation, create the appropriate documentation first.

The goal is that no important engineering knowledge is lost when the conversation ends.

## 4. Generate Session Index

After all engineering artifacts have been reviewed and updated, generate a downloadable:

session-index.md

The session index should contain:

- Session summary
- Stories completed
- Current story
- Next recommended story
- Engineering artifacts created
- Engineering artifacts updated
- Files changed
- Architectural decisions
- Bugs fixed
- Outstanding work
- Next recommended starting point
- Files likely needed next session
- Immediate first task

The session index should summarize and reference durable artifacts rather than duplicating them.

## 5. Completion Checklist

Report the result of reviewing each category.

Example:

✓ ADRs
✓ Architecture Documentation
✓ Specifications
✓ Database Documentation
✓ Engineering Principles
✓ Working Agreement
✓ AI Collaboration Documentation
✓ Behavior Tests
✓ Backlog
✓ Session Index Generated

## Guiding Principle

An engineering session is not complete until ephemeral conversation has been converted into durable engineering knowledge.

The objective is that a future engineering session can begin immediately using only the project's engineering artifacts, without depending on previous conversation history.