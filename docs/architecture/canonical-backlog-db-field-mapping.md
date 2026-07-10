# Canonical Backlog DB Field Mapping

**Project:** Johnny-Johnny Agent  
**Story:** design-canonical-backlog-persistence  
**Status:** Implemented baseline  
**Purpose:** Map every current `backlog.yml` field to the first PostgreSQL canonical backlog schema.


## Implementation Verification

The mapping is implemented by the PostgreSQL repository and persistence workflows. The live sandbox import/export round trip verified 21 epics, 198 issues, 68 acceptance criteria, and 25 comments.

The exported YAML was semantically identical to the imported document. Provider-metadata key order changed, which is acceptable because YAML mapping order is not domain state.

Supported interfaces:

```text
jj backlog db check
jj backlog db import
jj backlog db export
```

Normal backlog reads and mutations use PostgreSQL directly and do not pass through YAML.

---

## Import Root

Current YAML root:

```yaml
version: 1
project:
  provider: github
  title: MycroftAI Engineering Roadmap
  number: 1
  url: https://github.com/users/ggortsema/projects/1
  provider_metadata:
    github:
      project_id: PVT_kwHOA_XBWs4BZotz
```

---

## Seed / Import Assumptions

Initial import defaults:

```text
user.display_name = Grant Gortsema
provider.key = github
provider_account.username = ggortsema
provider_project.title = MycroftAI Engineering Roadmap
```

Canonical lookup path:

```text
github / ggortsema / MycroftAI Engineering Roadmap
```

---

## Project Mapping

| YAML Field | DB Destination | Notes |
|---|---|---|
| `project.provider` | `providers.key` | Upsert provider. Initial value: `github`. |
| `project.title` | `provider_projects.title` | Provider-level project/backlog title. Current value: `MycroftAI Engineering Roadmap`. |
| `project.number` | `provider_projects.external_number` | GitHub project number. Nullable for other providers. |
| `project.url` | `provider_projects.url` | Provider project URL. |
| `project.provider_metadata` | `provider_projects.provider_metadata` | Preserve raw provider metadata as JSONB. |
| `project.provider_metadata.github.project_id` | `provider_projects.external_id` | First-class provider project id when available. |

---

## Epic / Issue Mapping

Epics and issues both become rows in `backlog_items`.

| YAML Field | DB Destination | Notes |
|---|---|---|
| `id` | `backlog_items.canonical_id` | Stable canonical item identity within a provider project. |
| `type` | `backlog_items.item_type` | Current values: `epic`, `issue`. |
| `title` | `backlog_items.title` | Required. |
| `repository` | `backlog_items.repository` | Required today because the provider project spans multiple repositories. |
| `status` | `backlog_items.status` | Project/backlog status column value. |
| `issue_state` | `backlog_items.issue_state` | Provider issue state such as `OPEN` or `CLOSED`. |
| `order` | `backlog_items.item_order` | Canonical sibling order. |
| `description` | `backlog_items.description` | Defaults to empty string on YAML load. |
| `acceptance_criteria` | `backlog_item_acceptance_criteria` | Imported as ordered rows. `checked` defaults to `false`. |
| `comments` | `backlog_item_comments` | Imported as ordered rows. |
| `labels` | `backlog_item_labels` | Imported as one row per label. |
| `assignees` | `backlog_item_assignees` | Imported as one row per assignee. |
| `milestone` | `backlog_items.milestone` | Nullable. |
| `provider_metadata` | `backlog_items.provider_metadata` | Preserve raw provider metadata as JSONB. |
| `provider_metadata.github.issue_id` | `backlog_items.external_id` | First-class provider item id when available. |
| `provider_metadata.github.database_id` | `backlog_items.external_database_id` | GitHub database id when available. |
| `provider_metadata.github.number` | `backlog_items.external_number` | GitHub issue number when available. |
| `provider_metadata.github.url` | `backlog_items.external_url` | Provider item URL when available. |
| `provider_metadata.github.project_item_id` | `backlog_items.external_project_item_id` | GitHub project item id when available. |

---

## Hierarchy Mapping

Current YAML hierarchy:

```text
epics[]
  issues[]
```

Database hierarchy:

```text
backlog_items.parent_item_id
```

Rules:

| YAML Location | DB Rule |
|---|---|
| Epic under `epics[]` | `item_type = epic`, `parent_item_id = null` |
| Issue under `epic.issues[]` | `item_type = issue`, `parent_item_id = owning epic row id` |

---

## Acceptance Criteria Mapping

Current YAML stores acceptance criteria as strings.

| YAML Field | DB Destination | Notes |
|---|---|---|
| list index | `backlog_item_acceptance_criteria.position` | Preserve source order. |
| string value | `backlog_item_acceptance_criteria.body` | Required. |
| not present | `backlog_item_acceptance_criteria.checked` | Defaults to `false`. |

---

## Comment Mapping

| YAML Field | DB Destination | Notes |
|---|---|---|
| `id` | `backlog_item_comments.canonical_comment_id` | Preserves comment identity from YAML. |
| `body` | `backlog_item_comments.body` | Required. |
| `source` | `backlog_item_comments.source` | Defaults to `johnny-johnny` if absent in existing loader behavior. |
| `created_at` | `backlog_item_comments.created_at` | Nullable. |
| `provider_metadata` | `backlog_item_comments.provider_metadata` | Preserve raw provider metadata as JSONB. |
| list index | `backlog_item_comments.position` | Preserve comment order. |

---

## Future-Ready Nullable Columns

The first schema includes several nullable columns because they represent stable domain concepts that are likely needed by audit, chat, sync, and provider workflows.

### `backlog_items`

```text
priority
created_by_user_id
updated_by_user_id
closed_by_user_id
created_at
updated_at
closed_at
archived_at
deleted_at
metadata
```

### `backlog_item_comments`

```text
created_by_user_id
updated_at
deleted_at
```

### `users`

```text
preferences
metadata
deleted_at
```

---

## Round-Trip Requirement

The first importer/exporter must support this validation loop:

```text
backlog.yml
  -> import into PostgreSQL
  -> export from PostgreSQL
  -> compare against original backlog.yml
```

The exported YAML should preserve the current version 1 shape:

```text
version
project
epics
issues
acceptance_criteria
comments
labels
assignees
provider_metadata
```

Some YAML formatting differences are acceptable. Semantic differences are not.

---

## Non-Goals for First Population Script

The first population script does not attempt to model:

```text
provider_item_projections
sync history
audit history
webhook delivery history
chat operation history
GitHub timeline events
GitHub reactions
GitHub check runs
```

Those can be added later without remodeling the core provider/project/item spine.
