# ADR-001: Canonical First

## Status
Accepted

## Context
The canonical model is the SSOT.

## Decision
All mutations occur against the canonical model. Providers are projections reconciled from canonical state.

## Consequences
Avoid provider lock-in, deterministic behavior.

## Future Direction
This decision should remain stable. New capabilities should build upon it rather than bypass it.
