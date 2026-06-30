# ADR-101: Why Canonical First

## Status
Accepted

## Context
Early prototypes treated GitHub Projects as the source of truth. This coupled Johnny-Johnny to GitHub concepts and made deterministic engineering difficult.

## Alternatives Considered
- GitHub as SSOT
- Bidirectional peer models
- Canonical domain model

## Decision
Johnny-Johnny owns a provider-neutral canonical model. Providers are projections.

## Rationale
This enables deterministic reconciliation, portability, testing, offline mutations, and future provider support.

## Consequences
GitHub is no longer the editing surface. Users interact with Johnny-Johnny instead.
