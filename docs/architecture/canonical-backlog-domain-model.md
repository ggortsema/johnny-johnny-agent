# Canonical Backlog Domain Model

## Purpose
Describe the core domain model independent of storage technology.

## Core Concepts
- User
- Provider
- Provider Account
- Provider Project (canonical backlog)
- Backlog Item

## Hierarchy
User
└── Provider Account
    └── Provider Project
        └── Backlog Item
            ├── Acceptance Criteria
            ├── Comments
            ├── Labels
            └── Assignees

## Key Principles
- PostgreSQL is the canonical runtime store.
- YAML is an import/export format.
- Ordering is canonical domain data.
- Epics and issues are Backlog Items distinguished by type and hierarchy.
- Repositories identify implementation targets, not backlog identity.

See `canonical-backlog-domain-model-erd.md` for the ERD.
