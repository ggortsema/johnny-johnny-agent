# Engineering Principle Addition: External Boundaries Require Orchestration

## External Boundaries Require Orchestration

A command is sufficient only when the work is internal to the program or to a tightly controlled local boundary.

When Johnny-Johnny asks another system to change state, it is no longer merely running a command. It is orchestrating a state transition across an external boundary.

External systems may:

- accept a request
- reject a request
- throttle the caller
- partially apply a request
- return an ambiguous result
- succeed while Johnny-Johnny fails before recording success
- later drift from the requested state

Therefore provider-facing work should be modeled as orchestration:

- durable intent
- ordered operations
- idempotency
- retries and backoff
- failure routing
- pause and resume
- audit history
- reconciliation after partial success

Guiding distinction:

```text
If the work is internal, a command may be enough.
If the work crosses a system boundary, Johnny-Johnny is orchestrating.
```

This principle applies to provider reconciliation, GitHub/Jira synchronization, webhook handling, database-backed execution, and future queued workers.
