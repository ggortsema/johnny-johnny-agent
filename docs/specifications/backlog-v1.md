# Johnny-Johnny Backlog YAML Specification v1

## Purpose

The Johnny-Johnny Backlog YAML format is the canonical source of truth for project-management backlog data.

Version 1 supports a single project target while allowing each epic and issue to explicitly declare the repository in which it should be created. This supports GitHub Projects that span multiple repositories without relying on implicit inheritance.

It represents the desired backlog structure independently from GitHub, Jira, Linear, ClickUp, Azure DevOps, StyxCD, or any other execution or project-management provider.

This format is intended to support:

- Epics
- Child issues
- Stable provider-neutral IDs
- Portable work state
- Descriptions
- Acceptance criteria
- Lightweight planning metadata

Provider configuration, workflow execution settings, credentials, provider issue IDs, URLs, and project-board metadata are intentionally excluded from the canonical backlog document.

## Version

Every backlog document must include:

```yaml
version: 1
```

The `version` field identifies the schema version used to validate the document.

## Top-Level Structure

```yaml
version: 1

project:
  provider: github
  name: "MycroftAI Engineering Roadmap"

epics:
  - id: project-management-workflow-provider
    name: "Project Management Workflow Provider"
    state: todo
    description: "..."
    acceptanceCriteria:
      - "..."
    issues:
      - id: define-pm-workflow-dsl
        name: "Define PM Workflow DSL"
        state: todo
        description: "..."
```

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `version` | integer | yes | Backlog YAML schema version. Must be `1`. |
| `project` | object | yes | Target project for this backlog projection. |
| `epics` | array | yes | List of top-level epics. Must contain at least one epic. |

## Epic Object

An epic represents a top-level unit of backlog organization.

### Required Epic Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `id` | string | yes | Stable Johnny-Johnny ID. Not a provider ID. |
| `name` | string | yes | Human-readable epic name. |
| `repository` | string | yes | Repository where this epic issue will be created. |
| `state` | string | yes | Canonical portable work state. |
| `description` | string | yes | Epic description. May be an empty string. |
| `issues` | array | yes | Child issues under the epic. May be empty. |

### Optional Epic Fields

| Field | Type | Description |
|---|---:|---|
| `acceptanceCriteria` | array of strings | Human-readable acceptance criteria. |
| `labels` | array of strings | Portable labels. |
| `assignees` | array of strings | Portable assignee identifiers or names. |
| `milestone` | string | Portable milestone name. |

## Issue Object

An issue represents a child work item under an epic.

### Required Issue Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `id` | string | yes | Stable Johnny-Johnny ID. Not a provider ID. |
| `name` | string | yes | Human-readable issue name. |
| `repository` | string | yes | Repository where this issue will be created. |
| `state` | string | yes | Canonical portable work state. |
| `description` | string | yes | Issue description. May be an empty string. |

### Optional Issue Fields

| Field | Type | Description |
|---|---:|---|
| `acceptanceCriteria` | array of strings | Human-readable acceptance criteria. |
| `labels` | array of strings | Portable labels. |
| `assignees` | array of strings | Portable assignee identifiers or names. |
| `milestone` | string | Portable milestone name. |

## Stable IDs

The `id` field is a provider-neutral Johnny-Johnny identifier.

It is not a GitHub issue number, GitHub node ID, Jira key, Linear ID, or provider-specific project item ID.

Stable IDs are used to match backlog items across imports, exports, synchronization, and provider migrations.

### ID Format

IDs must use lowercase kebab-case:

```text
define-pm-workflow-dsl
```

Valid examples:

```text
project-management-workflow-provider
implement-github-issues-provider
support-dry-run-mode
```

Invalid examples:

```text
Define PM Workflow DSL
define_pm_workflow_dsl
define.pm.workflow.dsl
```

## Canonical State

The `state` field represents portable work state.

Allowed values:

| State | Meaning |
|---|---|
| `todo` | Work has not started. |
| `in_progress` | Work is actively being worked on. |
| `done` | Work is complete. |
| `blocked` | Work cannot proceed because of a dependency or issue. |
| `wont_do` | Work has been intentionally abandoned or rejected. |

Provider-specific statuses should be mapped into these canonical states during import.

Examples:

| Provider Status | Canonical State |
|---|---|
| GitHub Todo | `todo` |
| GitHub In Progress | `in_progress` |
| GitHub Done | `done` |
| Jira Backlog | `todo` |
| Jira In Progress | `in_progress` |
| Jira Done | `done` |

## Intentionally Excluded Fields

The canonical backlog YAML must not include:

- `workflow`
- `jenkins_creds`
- GitHub issue IDs
- GitHub node IDs
- GitHub project item IDs
- Provider URLs
- Provider-specific status values
- Runtime credentials

Those fields belong in a StyxCD workflow wrapper, provider metadata document, or synchronization report.

## Validation

This specification is validated by the JSON Schema:

```text
schemas/backlog-v1.schema.json
```

A valid Johnny-Johnny backlog YAML document must:

1. Parse as YAML.
2. Conform to the v1 JSON Schema.
3. Be convertible into the Johnny-Johnny canonical backlog model.

## Round-Trip Contract

The expected v1 round-trip contract is:

```text
GitHub Project
    ↓
Backlog model
    ↓
backlog.yml
    ↓
JSON Schema validation
    ↓
Backlog model
    ↓
Comparison
```

A generated `backlog.yml` should validate immediately after generation.

Johnny-Johnny should not consider an export successful unless the generated YAML validates against this schema.

## Compatibility

Version 1 is intentionally small.

Future versions may add:

- Nested issue hierarchies
- Provider metadata sidecars
- Priority
- Estimates
- Iterations
- Dependencies
- Multiple backlog item types

Any future breaking changes should increment the top-level `version` field.
