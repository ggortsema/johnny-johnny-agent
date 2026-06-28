th# Epic: Backlog-as-Code Synchronization

## Goal

Create a portable project-management synchronization engine that treats
GitHub Projects as a planning interface while maintaining a
provider-independent Source of Truth (SSOT).

The synchronization engine must support bidirectional synchronization
between GitHub and the canonical backlog model while preserving
portability across future providers such as Jira, Bitbucket, Azure
DevOps, or Linear.

## Success Criteria

-   GitHub can be exported into the canonical backlog model.
-   Canonical backlog can regenerate GitHub.
-   Synchronization is idempotent.
-   Human-readable backlog is generated automatically.
-   Provider-specific metadata remains isolated.
-   StyxCD uses this system to manage its own roadmap.

------------------------------------------------------------------------

## Stories

1.  **Design Canonical Backlog Model**
    -   Define portable backlog.yml schema.
    -   Support epics, stories, acceptance criteria, provider metadata.
2.  **Implement GitHub Project Export**
    -   Read GitHub Projects, Issues, labels, milestones, priorities,
        estimates, relationships.
3.  **Generate Canonical `backlog.yml`**
    -   Stable deterministic output.
    -   Idempotent generation.
    -   Provider metadata isolated.
4.  **Generate Human-Readable `backlog.md`**
    -   Organized by epic.
    -   Acceptance criteria included.
    -   GitHub links included.
5.  **Detect Backlog Changes**
    -   Detect additions, deletions, renames, status changes, priority
        changes, moved stories.
6.  **Generate Synchronization Report**
    -   Added, updated, removed, duplicate, warning, and error
        reporting.
7.  **Regenerate GitHub From SSOT**
    -   Create/update issues.
    -   Restore project assignments and metadata.
    -   Preserve relationships.
8.  **Implement Idempotent Synchronization**
    -   Safe repeated execution.
    -   Matching by provider ID then title.
9.  **Implement Dry-Run Mode**
    -   Preview create/update/delete/no-op actions.
10. **Support Provider Adapters**
    -   GitHub first.
    -   Architecture supports Jira, Azure DevOps, Bitbucket, Linear.
11. **Dogfood Backlog-as-Code Synchronization**
    -   Export StyxCD roadmap.
    -   Generate canonical backlog.
    -   Regenerate GitHub.
    -   Validate round-trip.
    -   Document the demonstration.

## Long-Term Vision

GitHub becomes the planning interface.

The canonical backlog model becomes the durable engineering model.

Markdown documentation is generated automatically.

Future providers become adapters rather than rewrites.

Kharon can consume both the canonical backlog and generated
synchronization history to reason about engineering intent and roadmap
evolution.
