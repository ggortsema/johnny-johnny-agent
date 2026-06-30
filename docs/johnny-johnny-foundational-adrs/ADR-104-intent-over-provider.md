# ADR-104: Intent Over Provider Workflows

## Status
Accepted

## Context
GitHub exposes provider-specific workflows that should not define Johnny-Johnny's API.

## Decision
Commands express engineering intent (create-issue, move-issue, update-epic) rather than provider operations.

## Consequences
Changing providers should not change the public CLI.
