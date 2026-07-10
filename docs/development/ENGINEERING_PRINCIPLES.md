# Engineering Principles

Version: 1.1
Last Updated: July 10, 2026

## Purpose

This document describes how Johnny-Johnny should be designed.

## Principles

### Domain First
The canonical domain model is provider independent.

### Provider Adapters
Provider-specific behavior belongs in adapters, not the domain.

### Stable IDs
Canonical IDs are permanent identities.

Provider identifiers, issue numbers, URLs, and project-item ids are projection metadata. They may change without changing canonical identity.

### Canonical Runtime State

PostgreSQL is the canonical runtime store for backlog state.

Portable files such as YAML are explicit import/export boundaries. Normal runtime workflows must not use files as hidden intermediaries between the domain and persistence.

### Explicit Cross-Boundary Consistency

A database and an external provider cannot share one ACID transaction. Workflows that cross those boundaries must make partial failure behavior explicit through idempotency, compensation, durable state, or clear consistency errors.

Never report success when canonical and required provider state are known to disagree.

### Organize by Domain Capability

Organize work by the domain capability being improved, not by the implementation being modified.

When assigning backlog items to epics, always ask:

> **What capability is becoming better?**

Do **not** organize work based on:

- source code layout
- programming language
- framework
- technology
- file being changed

Instead, organize work around business capabilities and bounded contexts.

Examples:

- Improving backlog CLI commands belongs to **Backlog as Code**, even though the implementation is in the CLI.
- Improving GitHub synchronization belongs to **Backlog as Code**, even though the implementation is in the GitHub adapter.
- Improving workflow planning belongs to **Project Management Workflow Provider**, regardless of which modules are modified.

The implementation location is an implementation detail.

The capability being improved defines the work.

### Reuse Before Duplication
Extract shared behavior after it is proven useful.

### Simplicity First
Choose the simplest solution that can evolve cleanly.

### Explicit Over Magic
Prefer obvious code and predictable behavior.

### Consistent CLI
Commands should feel like one application.
List commands should use consistent table formatting.
Filtering should follow include/exclude conventions.

### Behavior Before Implementation

Define the desired behavior before deciding how it should be implemented.

Behavior should be captured through:

- domain language
- acceptance criteria
- behavior tests
- documentation

Implementation details may change over time.

The expected behavior should remain stable.


### Durable Knowledge

Engineering knowledge should be preserved as durable project artifacts rather than remaining in conversation.

When important knowledge emerges, promote it into the appropriate artifact:

- ADRs
- Working Agreement
- Engineering Principles
- Specifications
- AI Collaboration documentation
- Behavior tests
- Backlog stories

Do not rely on memory when an engineering artifact should exist.



See `WORKING_AGREEMENT.md` for development workflow.
