# Johnny-Johnny Backlog YAML Specification v1

## Purpose

The Johnny-Johnny Backlog YAML format is the canonical source of truth (SSOT) for project-management backlog data.

The YAML is machine-owned. Johnny-Johnny loads the canonical model, performs mutations, validates the result, and deterministically serializes it back to YAML.

GitHub and future project-management providers are projections of this model rather than the source of truth.

## Design Principles

- Stable Johnny-Johnny IDs are the semantic identity.
- Provider-specific identifiers are projection metadata.
- `status` represents project planning state.
- `issue_state` represents provider issue lifecycle state.
- Presentation order is independent of identity.
- Serialization is deterministic.
- Provider metadata is useful for reconciliation and diagnostics, but live provider state is authoritative during reconciliation.

## Version

Every backlog document must include:

```yaml
version: 1
```

## Top-Level Structure

```yaml
version: 1

project:
  provider: github
  title: MycroftAI Engineering Roadmap
  number: 1
  url: https://github.com/users/ggortsema/projects/1
  provider_metadata:
    github:
      project_id: PVT_xxxxx

epics:
  - id: backlog-as-code-synchronization
    type: epic
    title: Backlog-as-Code Synchronization
    repository: ggortsema/styxcd-docs
    status: Backlog
    issue_state: OPEN
    order: 1000
    description: |
      Create a portable synchronization engine.
    acceptance_criteria: []
    labels: []
    assignees: []
    milestone: null
    provider_metadata:
      github:
        issue_id: I_xxxxx
        project_item_id: PVTI_xxxxx
        database_id: 12345
        number: 393
        url: https://github.com/...
    issues:
      - id: design-canonical-backlog-model
        type: issue
        title: Design Canonical Backlog Model
        repository: ggortsema/styxcd-docs
        status: Backlog
        issue_state: OPEN
        order: 1000
        description: |
          Define the canonical backlog model.
        acceptance_criteria: []
        labels: []
        assignees: []
        milestone: null
        provider_metadata:
          github:
            issue_id: I_xxxxx
            project_item_id: PVTI_xxxxx
            database_id: 12346
            number: 394
            url: https://github.com/...
```

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `version` | integer | yes | Backlog YAML schema version. Must be `1`. |
| `project` | object | yes | Project projection metadata. |
| `epics` | array | yes | Top-level epics in deterministic order. |

## Project Object

| Field | Type | Required | Description |
|---|---:|---:|---|
| `provider` | string | yes | Primary provider for this projection, for example `github`. |
| `title` | string | yes | Project title. |
| `number` | integer or null | no | Provider project number when available. |
| `url` | string or null | no | Provider project URL when available. |
| `provider_metadata` | object | yes | Provider-specific project metadata. |

## Epic Object

An epic represents a top-level backlog item.

| Field | Type | Required | Description |
|---|---:|---:|---|
| `id` | string | yes | Stable Johnny-Johnny ID. |
| `type` | string | yes | Must be `epic`. |
| `title` | string | yes | Human-readable title. |
| `repository` | string | yes | Repository where this item is projected. |
| `status` | string | yes | Project planning status, for example `Backlog`, `Ready`, `In Progress`, `In Review`, or `Done`. |
| `issue_state` | string | yes | Provider issue lifecycle state, for example `OPEN` or `CLOSED`. |
| `order` | integer | yes | Provider-neutral presentation order. |
| `description` | string | yes | Item description. May be empty. |
| `acceptance_criteria` | array of strings | yes | Human-readable acceptance criteria. May be empty. |
| `labels` | array of strings | yes | Labels. May be empty. |
| `assignees` | array of strings | yes | Assignees. May be empty. |
| `milestone` | string or null | yes | Milestone value, or `null`. |
| `provider_metadata` | object | yes | Provider-specific metadata for this item. |
| `issues` | array | yes | Child issues under the epic. May be empty. |

## Issue Object

An issue represents a child backlog item under an epic.

| Field | Type | Required | Description |
|---|---:|---:|---|
| `id` | string | yes | Stable Johnny-Johnny ID. |
| `type` | string | yes | Must be `issue`. |
| `title` | string | yes | Human-readable title. |
| `repository` | string | yes | Repository where this item is projected. |
| `status` | string | yes | Project planning status. |
| `issue_state` | string | yes | Provider issue lifecycle state. |
| `order` | integer | yes | Provider-neutral presentation order. |
| `description` | string | yes | Item description. May be empty. |
| `acceptance_criteria` | array of strings | yes | Human-readable acceptance criteria. May be empty. |
| `labels` | array of strings | yes | Labels. May be empty. |
| `assignees` | array of strings | yes | Assignees. May be empty. |
| `milestone` | string or null | yes | Milestone value, or `null`. |
| `provider_metadata` | object | yes | Provider-specific metadata for this item. |

## Stable IDs

The `id` field is a provider-neutral Johnny-Johnny identifier.

It is not a GitHub issue number, GitHub node ID, Jira key, Linear ID, or provider-specific project item ID.

Stable IDs are used to match backlog items across imports, exports, synchronization, mutation commands, and provider migrations.

IDs must use lowercase kebab-case:

```text
define-canonical-backlog-model
```

## Status vs Issue State

`status` and `issue_state` are intentionally separate.

### `status`

`status` is the project planning state.

Examples:

```yaml
status: Backlog
status: Ready
status: In Progress
status: In Review
status: Done
```

This is the state changed by commands like:

```bash
jj backlog update-issue implement-idempotent-synchronization --status Done
```

### `issue_state`

`issue_state` is the provider issue lifecycle state.

For GitHub, common values are:

```yaml
issue_state: OPEN
issue_state: CLOSED
```

Closing a GitHub issue is separate from moving the issue to a project status such as `Done`.

## Ordering

Ordering is independent of identity.

Recommended values:

```text
1000
2000
3000
```

New work can be inserted between existing items, for example:

```text
1500
```

without renumbering the entire backlog.

## Provider Metadata

`provider_metadata` contains provider-specific identifiers required for efficient synchronization and diagnostics.

These values may change when provider objects are recreated and are not part of semantic identity.

Example:

```yaml
provider_metadata:
  github:
    issue_id: I_xxxxx
    project_item_id: PVTI_xxxxx
    database_id: 12345
    number: 393
    url: https://github.com/...
```

Provider metadata is advisory. During reconciliation, Johnny-Johnny compares the desired canonical model with live provider state.

## Hidden GitHub Metadata

When publishing to GitHub, Johnny-Johnny embeds a hidden metadata block in issue bodies:

```text
<!-- johnny-johnny
id: design-canonical-backlog-model
type: issue
parent: backlog-as-code-synchronization
-->
```

For epics:

```text
<!-- johnny-johnny
id: backlog-as-code-synchronization
type: epic
-->
```

This allows Johnny-Johnny to recover stable semantic identity and parent relationships from GitHub if necessary.

## Reconciliation Concepts

Johnny-Johnny reconciles desired state against live provider state.

Important relationships and properties include:

- Issue existence
- Project membership
- Epic parentage
- Project planning status
- Issue lifecycle state
- Title
- Description
- Labels
- Assignees
- Milestone

Current operation vocabulary includes:

- `CreateEpicOperation`
- `CreateIssueOperation`
- `AddIssueToProjectOperation`
- `AttachIssueToEpicOperation`

Future operations may include:

- `UpdateIssueStatusOperation`
- `UpdateIssueStateOperation`
- `UpdateIssueTitleOperation`
- `UpdateIssueBodyOperation`

## Round Trip

```text
GitHub Project
    ↓
Generate
    ↓
Canonical backlog.yml
    ↓
Mutate
    ↓
Validate
    ↓
Serialize
    ↓
Reconcile
    ↓
GitHub Project
```

A generated `backlog.yml` should validate immediately after generation.

A reconciled project should generate a canonical YAML that produces zero operations on the next dry run when there is no drift.

## Compatibility

Earlier v1 drafts used:

- `name`
- normalized `state`
- `acceptanceCriteria`
- provider IDs excluded from the canonical YAML

The frozen v1 model uses:

- `title`
- project planning `status`
- provider lifecycle `issue_state`
- `acceptance_criteria`
- isolated `provider_metadata`
