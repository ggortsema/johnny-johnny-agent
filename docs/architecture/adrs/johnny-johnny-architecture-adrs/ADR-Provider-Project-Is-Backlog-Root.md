# ADR: Provider Project is the Backlog Root

## Status
Accepted

## Context
The backlog should not be identified by a repository. A canonical backlog may span multiple repositories.

## Decision
The canonical backlog identity is the provider project.

Identity hierarchy:

Provider -> Provider Account -> Provider Project -> Backlog Items

Example:

GitHub / ggortsema / MycroftAI Engineering Roadmap

Repositories remain attributes of backlog items, identifying implementation targets rather than backlog identity.

## Consequences
- Backlog identity is provider-independent.
- Multiple repositories can exist within one backlog.
- Future provider support (Jira, Linear, etc.) follows the same model.
