# ADR-102: Why Planner and Executor are Separate

## Status
Accepted

## Context
Planning and provider execution evolved together initially.

## Decision
Separate planning from execution.

Planner computes desired operations from canonical vs live state.
Executor performs provider-specific work.

## Benefits
- Dry-run becomes free.
- Execution is deterministic.
- Provider implementations stay isolated.
- New providers reuse the planner.
