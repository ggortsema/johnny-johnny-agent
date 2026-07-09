# ADR-002: Intent-Based Commands

## Status
Accepted

## Context
Users think in engineering tasks, not mutations.

## Decision
Expose create-issue, update-issue, create-epic, move-issue, etc. Hide implementation details.

## Consequences
CLI remains stable across providers.

## Future Direction
This decision should remain stable. New capabilities should build upon it rather than bypass it.
