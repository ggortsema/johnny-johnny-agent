# ADR-103: Why Immediate Reconciliation

## Status
Accepted

## Context
Deferred reconciliation creates hidden state between canonical data and providers.

## Decision
Every confirmed command reconciles immediately.

## Benefits
- No hidden drift.
- Simpler mental model.
- Easier debugging.
- Idempotent workflows.
