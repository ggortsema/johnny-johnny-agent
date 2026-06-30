# ADR-004: Command Pipeline

## Status
Accepted

## Context
Needed consistent command architecture.

## Decision
Load→Mutate→Validate→Plan→Persist→Execute.

## Consequences
Every capability follows one execution model.

## Future Direction
This decision should remain stable. New capabilities should build upon it rather than bypass it.
