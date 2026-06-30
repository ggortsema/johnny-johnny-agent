# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for **Johnny-Johnny**, a personal engineering assistant designed to help software engineers build, understand, maintain, and automate software projects.

Johnny-Johnny is project-agnostic. It is not tied to any specific product or codebase. It helps engineers organize work, reason about architecture, automate repetitive tasks, and build software through deterministic workflows backed by reusable capabilities.

Conversations are simply one interface to those capabilities.

---

# Vision

Johnny-Johnny is built around a few core principles:

- Build reusable capabilities before user interfaces.
- Treat the CLI as the primary public interface.
- Keep business logic independent from presentation layers.
- Prefer deterministic workflows whenever possible.
- Use AI where reasoning and intent resolution add value.
- Make every capability reusable from:
  - CLI
  - FastAPI
  - Future chat interfaces
  - LangGraph
  - Future desktop/web applications

Johnny-Johnny is intended to become a personal engineering operating system rather than a collection of unrelated tools.

---

# Design Principles

## Canonical First

The canonical domain model is the Source of Truth.

External systems such as GitHub are provider projections.

Users manipulate the canonical engineering model.

Johnny-Johnny reconciles provider state.

---

## Intent-Based Commands

Commands describe the user's intent rather than implementation details.

Examples:

- create-issue
- update-issue
- create-epic
- move-issue

rather than low-level mutation commands.

---

## Immediate Reconciliation

Confirmed commands mutate the canonical model and immediately reconcile provider state.

Johnny-Johnny intentionally avoids hidden state whenever practical.

After a successful `--confirm`, the canonical model and provider projection should agree.

---

## Provider Independence

Users interact with engineering concepts.

Johnny-Johnny understands provider-specific behavior.

Provider implementations should not dictate the public command surface.

---

## Grow Johnny-Johnny Instead of Workarounds

When normal engineering work requires leaving Johnny-Johnny, prefer adding a new capability rather than teaching users provider-specific workflows.

---

# Current Major Capability

## Backlog-as-Code

The first complete Johnny-Johnny capability is **Backlog-as-Code**.

The canonical Source of Truth (SSOT) is:

```
backlog.yml
```

GitHub Projects are treated as a projection of that canonical backlog.

```
CLI Command
        ↓
Load Canonical Model
        ↓
Mutate Domain
        ↓
Validate
        ↓
Planner
        ↓
Execution Plan
        ↓
Provider Adapter
        ↓
GitHub
```

The reconciliation engine is deterministic and idempotent.

Verified workflow:

1. Generate canonical backlog from GitHub.
2. Validate the YAML.
3. Create canonical issues.
4. Update canonical issues.
5. Delete canonical issues (maintenance).
6. Reconcile provider state.
7. Regenerate canonical backlog.
8. Dry-run reconciliation returns zero operations.

---

# Canonical Model

The canonical backlog separates:

- Stable semantic identity
- Planning state
- Provider lifecycle state
- Provider metadata

Example:

```yaml
id: create-issue-command
type: issue
title: Create Issue Command
status: Done
issue_state: OPEN

provider_metadata:
  github:
    issue_id: ...
    project_item_id: ...
```

Planning state and provider lifecycle are intentionally independent.

Provider metadata is advisory.

Live provider state is authoritative during reconciliation.

---

# Current CLI

## API

```bash
jj serve
```

---

## Backlog

### Generate

```bash
jj backlog generate
```

Generate canonical backlog from GitHub.

---

### Validate

```bash
jj backlog validate
```

---

### Inspect

```bash
jj backlog inspect
```

---

### List Epics

```bash
jj backlog list-epics
```

---

### Create Issue

```bash
jj backlog create-issue
```

Creates a canonical issue and immediately reconciles GitHub on confirmation.

---

### Update Issue

```bash
jj backlog update-issue
```

Updates canonical planning state and reconciles GitHub.

---

### Reconcile

```bash
jj backlog reconcile
```

Produces a reconciliation plan or executes it.

---

## Maintenance

### Purge

```bash
jj maintenance purge
```

Delete Johnny-managed GitHub issues.

---

### Delete Issue

```bash
jj maintenance delete-issue
```

Developer-oriented command used for testing and backlog cleanup.

---

# Architecture

```
CLI
    ↓
Capability
    ↓
Domain Mutation
    ↓
Validation
    ↓
Planner
    ↓
Execution Plan
    ↓
Provider Adapter
```

The planner computes the difference between:

```
Desired Canonical State

and

Live Provider State
```

The executor applies the resulting execution plan.

Provider adapters contain provider-specific implementation.

Business logic remains provider independent.

---

# Current Status

Completed:

- Canonical backlog domain model
- Canonical YAML specification
- JSON Schema validation
- GitHub exporter
- GitHub renderer
- Deterministic YAML generation
- Planner
- Executor
- Live-state reconciliation
- Idempotent synchronization
- Dry-run planning
- GitHub Project synchronization
- GitHub Epic/Sub-Issue synchronization
- Create Issue
- Update Issue (status)
- List Epics
- Maintenance Delete Issue
- Maintenance Purge
- Dogfooded Backlog-as-Code on Johnny-Johnny itself

The Backlog-as-Code capability has moved beyond import/export tooling into a complete canonical engineering workflow.

---

# Next Milestone

Complete the backlog capability:

- Create Epic
- Update Epic
- Expand Update Issue
- List Issues
- Find Issue
- Move Issue

Then expand Johnny-Johnny into additional engineering domains:

- GitHub
- Gmail
- Google Calendar
- Documentation
- Engineering Playbooks
- AI-assisted engineering workflows

---

# Development Philosophy

Every capability grows through small validated vertical slices.

```
Define Domain
        ↓
Implement Domain Mutation
        ↓
Validate
        ↓
Add Planning Rule
        ↓
Add Provider Execution
        ↓
Dogfood Through CLI
        ↓
Expose Through AI
```

Whenever possible, Johnny-Johnny should automate provider workflows so users remain focused on engineering intent rather than provider mechanics.

---

# Long-Term Direction

Backlog management is the first complete Johnny-Johnny capability.

The architecture established by Backlog-as-Code is intended to become the foundation for future capabilities including:

- GitHub
- Gmail
- Calendar
- Documentation
- Knowledge Management
- Project Planning
- Engineering Automation
- Playbook Execution

Each capability should follow the same execution model:

```
Intent
    ↓
Canonical Model
    ↓
Planner
    ↓
Execution Plan
    ↓
Provider
```

This consistent architecture allows Johnny-Johnny to grow organically while preserving deterministic behavior and reusable engineering capabilities.

---

# License

TBD