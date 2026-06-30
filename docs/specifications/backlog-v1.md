# Johnny-Johnny Backlog YAML Specification v1

## Purpose

The Johnny-Johnny Backlog YAML format is the canonical Source of Truth (SSOT) for project-management backlog data.

The YAML is machine-owned. Johnny-Johnny loads the canonical model, performs domain mutations, validates the result, and deterministically serializes it back to YAML.

GitHub Projects and future project-management providers are projections of this model rather than the source of truth.

## Design Principles

- Stable Johnny-Johnny IDs are the semantic identity.
- Provider-specific identifiers are projection metadata.
- `status` represents project planning state.
- `issue_state` represents provider issue lifecycle state.
- Presentation order is independent of identity.
- Serialization is deterministic.
- Provider metadata is useful for reconciliation and diagnostics, but live provider state is authoritative during reconciliation.
- Commands should mutate the canonical model and reconcile providers rather than requiring users to work directly in provider UIs.

## Version

Every backlog document must include:

```yaml
version: 1
```

The current schema version remains `1`.

The v1 model is intentionally minimal. New commands should not require schema changes unless the canonical engineering domain itself gains a new concept.

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
| `id` | string | yes | Stable Johnny-Johnny ID. Must be lowercase kebab-case. |
| `type` | string | yes | Must be `epic`. |
| `title` | string | yes | Human-readable title. |
| `repository` | string | yes | Repository where this item is projected. |
| `status` | enum | yes | Project planning status. Must be one of `Backlog`, `Ready`, `In Progress`, `In Review`, or `Done`. |
| `issue_state` | enum | yes | Provider issue lifecycle state. Must be `OPEN` or `CLOSED`. |
| `order` | integer | yes | Provider-neutral presentation order. Must be `0` or greater. |
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
| `id` | string | yes | Stable Johnny-Johnny ID. Must be lowercase kebab-case. |
| `type` | string | yes | Must be `issue`. |
| `title` | string | yes | Human-readable title. |
| `repository` | string | yes | Repository where this item is projected. |
| `status` | enum | yes | Project planning status. Must be one of `Backlog`, `Ready`, `In Progress`, `In Review`, or `Done`. |
| `issue_state` | enum | yes | Provider issue lifecycle state. Must be `OPEN` or `CLOSED`. |
| `order` | integer | yes | Provider-neutral presentation order. Must be `0` or greater. |
| `description` | string | yes | Item description. May be empty. |
| `acceptance_criteria` | array of strings | yes | Human-readable acceptance criteria. May be empty. |
| `labels` | array of strings | yes | Labels. May be empty. |
| `assignees` | array of strings | yes | Assignees. May be empty. |
| `milestone` | string or null | yes | Milestone value, or `null`. |
| `provider_metadata` | object | yes | Provider-specific metadata for this item. |

## Stable IDs

The `id` field is a provider-neutral Johnny-Johnny identifier.

It is not a GitHub issue number, GitHub node ID, Jira key, Linear ID, or provider-specific project item ID.

Stable IDs are used to match backlog items across imports, exports, synchronization, mutation commands, provider migrations, and provider recovery.

IDs must use lowercase kebab-case:

```text
define-canonical-backlog-model
```

The schema pattern is:

```text
^[a-z0-9]+(?:-[a-z0-9]+)*$
```

## Status vs Issue State

`status` and `issue_state` are intentionally separate.

### `status`

`status` is the project planning state.

Allowed values:

```yaml
status: Backlog
status: Ready
status: In Progress
status: In Review
status: Done
```

This is the state changed by commands like:

```bash
jj backlog update-issue create-issue-command --status Done --confirm
```

Epic status is also modeled as planning state. Updating an epic status should update the epic itself. Child issue status should not cascade unless an explicit future command option requests that behavior.

### `issue_state`

`issue_state` is the provider issue lifecycle state.

Allowed values:

```yaml
issue_state: OPEN
issue_state: CLOSED
```

Closing a provider issue is separate from moving the item to a project status such as `Done`.

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

The schema intentionally leaves `provider_metadata` open-ended so each provider can store its own projection-specific values.

## Hidden GitHub Metadata

When publishing to GitHub, Johnny-Johnny embeds a hidden metadata block in issue bodies.

For issues:

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

Johnny-Johnny reconciles desired canonical state against live provider state.

Important relationships and properties include:

- Epic existence
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
- `UpdateIssueStatusOperation`
- `DeleteIssueOperation`

Expected future operations may include:

- `UpdateEpicStatusOperation`
- `UpdateEpicTitleOperation`
- `UpdateEpicBodyOperation`
- `UpdateIssueStateOperation`
- `UpdateIssueTitleOperation`
- `UpdateIssueBodyOperation`
- `MoveIssueOperation`

## Command Model

Backlog commands operate against the canonical model.

Confirmed commands should generally follow this flow:

```text
Load canonical backlog
    ↓
Mutate domain model
    ↓
Validate
    ↓
Save canonical YAML
    ↓
Plan reconciliation
    ↓
Execute provider operations
```

The intent is that successful confirmed commands leave the canonical model and provider projection in agreement.

Examples of current and planned commands:

```bash
jj backlog create-issue --epic backlog-as-code-synchronization --title "Create Issue Command" --confirm
jj backlog update-issue create-issue-command --status Done --confirm
jj backlog list-epics
jj backlog reconcile --file data/input/backlog/backlog.yml --dry-run
jj maintenance delete-issue delete-me-test-issue --confirm
```

## Maintenance Commands

Maintenance commands are not normal user backlog workflow commands.

They are used for development, repair, cleanup, or testing.

Examples:

```bash
jj maintenance purge --project "MycroftAI Engineering Roadmap" --confirm
jj maintenance delete-issue delete-me-test-issue --confirm
```

Maintenance commands may perform destructive provider operations and should require explicit confirmation.

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

Expected clean-state result:

```text
Execution Plan

No operations.

Operations: 0
```

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

## Schema Parity Notes

This specification is intended to match `backlog-v1.schema.json`.

The schema currently enforces:

- `version` must be `1`.
- `id` must be lowercase kebab-case.
- `status` must be one of `Backlog`, `Ready`, `In Progress`, `In Review`, or `Done`.
- `issue_state` must be one of `OPEN` or `CLOSED`.
- `type` must be `epic` for epics and `issue` for issues.
- `order` must be an integer greater than or equal to `0`.
- `provider_metadata` remains open-ended.
