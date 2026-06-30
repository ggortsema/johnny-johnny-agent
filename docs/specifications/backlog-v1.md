
# Johnny-Johnny Backlog YAML Specification v1

## Purpose

The Johnny-Johnny Backlog YAML format is the canonical source of truth (SSOT) for project-management backlog data.

The YAML is machine-owned. Johnny-Johnny loads the canonical model, performs mutations, validates the result, and deterministically serializes it back to YAML.

GitHub (and future providers) are projections of this model rather than the source of truth.

## Design Principles

- Stable Johnny-Johnny IDs are the semantic identity.
- GitHub identifiers are projection metadata.
- GitHub status values are preserved exactly; they are **not** normalized.
- Presentation order is independent of identity.
- Serialization is deterministic.

## Version

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
    status: OPEN
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
        status: OPEN
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

## Required Fields

### Project

- provider
- title
- provider_metadata

### Epic

- id
- type (`epic`)
- title
- repository
- status
- order
- description
- acceptance_criteria
- labels
- assignees
- milestone
- provider_metadata
- issues

### Issue

- id
- type (`issue`)
- title
- repository
- status
- order
- description
- acceptance_criteria
- labels
- assignees
- milestone
- provider_metadata

## Stable IDs

The `id` field is a provider-neutral Johnny-Johnny identifier. It never changes when a provider object is recreated.

## Status

`status` preserves the provider value exactly (for example `OPEN`, `CLOSED`, `Todo`, `In Progress`, `Done`).

Johnny-Johnny does not normalize status values.

## Ordering

Ordering is independent of identity.

Recommended values:

```text
1000
2000
3000
```

New work can be inserted between existing items (for example `1500`) without renumbering everything.

## Provider Metadata

`provider_metadata` contains provider-specific identifiers required for efficient synchronization.

These values may change when provider objects are recreated and are not part of the semantic identity.

## Hidden GitHub Metadata

When publishing back to GitHub, Johnny-Johnny embeds a small hidden metadata block:

```text
<!-- johnny-johnny
id: design-canonical-backlog-model
type: issue
parent: backlog-as-code-synchronization
-->
```

This allows the canonical model to be reconstructed from GitHub if necessary.

## Round Trip

```text
GitHub Project
    ↓
Pull
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
