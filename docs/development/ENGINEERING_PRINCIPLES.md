# Engineering Principles

Version: 1.0
Last Updated: July 8, 2026

## Purpose

This document describes how Johnny-Johnny should be designed.

## Principles

### Domain First
The canonical domain model is provider independent.

### Provider Adapters
Provider-specific behavior belongs in adapters, not the domain.

### Stable IDs
Canonical IDs are permanent identities.

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

See `WORKING_AGREEMENT.md` for development workflow.
