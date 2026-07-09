# ADR-005: Planner / Executor Separation

## Status
Accepted

## Context
Planning and execution have different concerns.

## Decision
Planner computes operations. Executor performs provider work.

## Consequences
Dry-run becomes trivial.

## Future Direction
This decision should remain stable. New capabilities should build upon it rather than bypass it.
