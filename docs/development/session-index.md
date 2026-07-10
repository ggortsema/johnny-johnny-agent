# Session Index

**Date:** July 10, 2026  
**Project:** Johnny-Johnny Agent  
**Project Version:** 0.1.0  
**Git Branch:** dev  
**Current Story:** `design-canonical-backlog-persistence`  
**Next Story:** `expose-backlog-workflows-through-rest-api`

## Session Summary

This session completed the functional migration of Johnny-Johnny backlog runtime behavior from YAML-backed state to PostgreSQL-backed canonical persistence.

PostgreSQL now supplies normal backlog reads, targeted mutations, reconciliation, and purge behavior. YAML remains only as an explicit import/export, backup, migration, validation, and inspection format.

The session also established targeted GitHub synchronization for user-facing mutations. Create, update, move, and delete workflows synchronize the required GitHub projection before reporting success and use rollback, compensation, idempotent repair, and explicit consistency errors across the PostgreSQL/GitHub boundary.

The sandbox database and GitHub Project were used to validate the persistence and provider workflows. A full purge completed successfully. A full PostgreSQL-backed reconciliation was launched at session close, but its final completion and zero-operation verification were not confirmed in conversation.

## Stories Completed

### `design-canonical-backlog-persistence`

Implementation is functionally complete:

- canonical schema and provider seeds applied
- direct PostgreSQL connectivity verified
- YAML snapshot import/export implemented
- semantic round trip verified
- read commands migrated
- mutation commands migrated
- targeted GitHub projection workflows implemented
- delete, reconcile, and purge migrated
- bounded and explicit `--all` execution supported

The story should be moved to Done only after confirming the final full sandbox reconcile produces a zero-operation dry run. The exact backlog update is recorded in `docs/development/backlog-session-update-plan-2026-07-10.md`.

## Next Recommended Story

### `expose-backlog-workflows-through-rest-api`

Expose every supported PostgreSQL-backed application workflow through FastAPI without invoking the CLI or duplicating business logic.

The proposed story description and acceptance criteria are recorded in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Architectural Decisions

1. PostgreSQL is the canonical backlog runtime store.
2. YAML is an explicit import/export boundary and never a hidden runtime intermediary.
3. CLI migration is intentionally breaking; no parallel YAML-backed legacy commands are maintained.
4. Canonical IDs are stable identity; GitHub IDs, numbers, URLs, and project-item IDs are provider metadata.
5. `--project` resolves a stored provider-project binding; reconcile never silently rebinds by provider title.
6. Confirmed create/update/move/delete operations synchronize targeted GitHub state before reporting success.
7. PostgreSQL and GitHub consistency is managed through transaction rollback, compensation, idempotent retry, and explicit consistency errors.
8. Reconcile and purge support safe bounded execution and explicit `--all` execution.
9. Purge deletes provider projection state while preserving canonical PostgreSQL data.
10. REST and CLI are peer adapters over shared application workflows; REST must not shell out to `jj`.

See:

```text
docs/architecture/adrs/ADR-001-postgresql-canonical-backlog-runtime.md
docs/architecture/adrs/ADR-002-targeted-provider-synchronization.md
docs/architecture/canonical-backlog-runtime-architecture.md
```

## Engineering Artifacts Created

```text
docs/architecture/adrs/ADR-001-postgresql-canonical-backlog-runtime.md
docs/architecture/adrs/ADR-002-targeted-provider-synchronization.md
docs/architecture/canonical-backlog-runtime-architecture.md
docs/database/postgres/README.md
docs/development/backlog-persistence-test-strategy.md
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Engineering Artifacts Updated

```text
README.md
docs/specifications/backlog-v1.md
docs/architecture/canonical-backlog-domain-model.md
docs/architecture/canonical-backlog-db-field-mapping.md
docs/architecture/durable-reconciliation-execution-model.md
docs/development/ENGINEERING_PRINCIPLES.md
docs/development/DECISION_LOG.md
docs/development/README.md
docs/development/commands-left-off.txt
docs/database/postgres/001_create_canonical_backlog_tables.sql
docs/database/postgres/002_seed_core_providers.sql
docs/database/postgres/import_backlog_yaml.py
docs/database/postgres/export_backlog_yaml.py
```

## Production Code Added

```text
src/johnny_johnny_agent/capabilities/backlog_persistence/__init__.py
src/johnny_johnny_agent/capabilities/backlog_persistence/postgres.py
src/johnny_johnny_agent/capabilities/backlog_persistence/workflow.py
```

## Production Code Updated

```text
pyproject.toml
uv.lock
src/johnny_johnny_agent/config.py
src/johnny_johnny_agent/cli/main.py
src/johnny_johnny_agent/capabilities/backlog_sync/executor.py
src/johnny_johnny_agent/capabilities/backlog_sync/mutations.py
src/johnny_johnny_agent/capabilities/github/client.py
```

## Production Code Removed

The obsolete Markdown publish pipeline and old purge implementation were removed:

```text
src/johnny_johnny_agent/capabilities/backlog_sync/loader.py
src/johnny_johnny_agent/capabilities/backlog_sync/workflow.py
src/johnny_johnny_agent/capabilities/backlog_sync/parser/__init__.py
src/johnny_johnny_agent/capabilities/backlog_sync/parser/markdown.py
src/johnny_johnny_agent/capabilities/backlog_sync/purge.py
src/johnny_johnny_agent/capabilities/github/publisher.py
```

## Behavior Tests Added

```text
tests/behavior/test_backlog_database_cli.py
tests/behavior/test_backlog_postgres_persistence.py
tests/behavior/test_backlog_targeted_epic_creation.py
tests/behavior/test_backlog_targeted_mutations.py
tests/behavior/test_backlog_remaining_mutations.py
```

Existing CLI grammar and workflow tests were updated for the breaking PostgreSQL command surfaces.

Final automated result:

```text
70 passed, 1 skipped
```

## Runtime Commands Migrated

### Reads

```text
jj backlog inspect
jj backlog list epics
jj backlog list items
jj backlog describe
```

### Targeted mutations

```text
jj backlog create epic
jj backlog create issue
jj backlog update
jj backlog move
jj maintenance delete-issue
```

### Projection workflows

```text
jj backlog reconcile
jj maintenance purge
```

## Commands Intentionally Retained

```text
jj backlog pull          raw GitHub diagnostic
jj backlog validate      YAML schema validation
jj backlog db check      PostgreSQL readiness
jj backlog db import     YAML migration/restore
jj backlog db export     YAML backup/inspection
jj serve                 API server launcher
```

## Commands Deferred or Removed

Deferred:

```text
jj backlog generate
```

It remains temporarily GitHub-to-YAML and should later be replaced and renamed as direct provider-to-PostgreSQL import after durable provider execution is implemented.

Removed:

```text
jj backlog publish
jj backlog preview-epic-body
```

## Live Validation Completed

- PostgreSQL `styxcd` reached directly through `DATABASE_URL`.
- Schema `johnny_johnny` reported 9/9 canonical tables and five seeded providers.
- Sandbox YAML import stored 21 epics and 198 issues.
- Export round trip preserved all semantic data, including 68 acceptance criteria and 25 comments.
- Database-backed inspect/list/describe commands worked, including filters and YAML/JSON rendering.
- Targeted epic creation created GitHub issue `#1887` and persisted provider metadata.
- An existing canonical epic was repaired idempotently without creating a duplicate issue.
- Targeted issue creation, status/comment update, content update, move, and delete preview worked.
- Full provider purge completed while retaining canonical database state.
- Full reconcile was launched after purge; final completion remains to be verified.

## Bugs Discovered and Fixed

### PostgreSQL remote connectivity

Opening the AWS security-group port was insufficient because PostgreSQL listened only on `localhost` and `pg_hba.conf` allowed only local clients. The disposable sandbox was configured for direct development access. This public exposure is temporary and must be removed in the AWS server deployment pass.

### Incorrect sandbox provider binding

The imported sandbox project record contained the production MycroftAI GitHub Project ID. Targeted epic creation therefore added issue `#1887` to the wrong project. The database binding was corrected to GitHub Project number 3 / ID `PVT_kwHOA_XBWs4Bc90o`.

Durable lesson: project title selects the stored database row; the row's external ID determines the provider target. Reconcile must never infer or silently rewrite this binding.

### Create-epic retry blocked repair

The initial idempotent workflow rejected an existing canonical ID before attempting provider repair. It was corrected so an identical create request repairs or confirms the provider projection while conflicting content remains an error.

### YAML diff appeared destructive

A large textual diff after export was caused only by provider-metadata key ordering. Structural comparison confirmed the documents were semantically identical.

### Legacy publish cleanup

Removing the old publish command required deleting its exclusive Markdown loader, parser, workflow, publisher, and unused client helper. Temporary IDE warnings were caused by deletion order, not remaining dependencies.

## Lessons Learned

- Establish the reusable PostgreSQL domain-loading boundary once; subsequent read conversions become thin adapter changes.
- Outputting YAML does not imply YAML persistence.
- Provider project IDs are operationally critical metadata and require preflight/explicit rebinding behavior.
- User-facing mutation semantics should be designed from expected observable behavior, not only from storage boundaries.
- Cross-system transaction language must distinguish ACID guarantees from compensating workflows.
- Safe chunking and unattended `--all` modes are both necessary.
- Long-running purge/reconcile commands need future progress output.

## Outstanding Work

1. Verify the full sandbox reconcile completed and returns zero operations.
2. Apply the backlog status/comment and create the next REST story using the update plan.
3. Expose supported workflows through FastAPI with typed models and parity tests.
4. Replace/rename `generate` as direct GitHub-to-PostgreSQL import.
5. Persist durable reconcile runs and operations with retry/backoff and provider-aware throttling.
6. Add an explicit provider-project rebind command/workflow.
7. Add progress output for long purge and reconcile execution.
8. Move PostgreSQL behind private AWS networking, rotate the development credential, and remove public `5432` access.
9. Decide whether server-mode mutations remain synchronous or initially return operation/run resources for long workflows.

## Category Review

- **ADRs:** created two accepted ADRs.
- **Architecture documentation:** created runtime architecture and updated domain/reconciliation docs.
- **Specifications:** updated YAML v1 to define it as an exchange format rather than runtime SSOT.
- **Database documentation:** added runtime README and updated schema/mapping status.
- **Engineering Principles:** added canonical-runtime-state and cross-boundary-consistency principles.
- **Working Agreement:** reviewed; no change required.
- **AI Collaboration documentation:** reviewed; no change required.
- **Behavior tests:** expanded and verified at 70 passed, 1 skipped.
- **Backlog:** reviewed; canonical updates are recorded as commands because the closure environment cannot safely mutate the connected database.
- **Other documentation:** README and decision log updated.

## Files Likely Needed Next Session

```text
src/johnny_johnny_agent/api/app.py
src/johnny_johnny_agent/application.py
src/johnny_johnny_agent/cli/main.py
src/johnny_johnny_agent/domain/backlog.py
src/johnny_johnny_agent/capabilities/backlog_persistence/workflow.py
src/johnny_johnny_agent/capabilities/backlog_persistence/postgres.py
src/johnny_johnny_agent/capabilities/github/client.py
tests/behavior/test_backlog_cli_workflows.py
tests/behavior/test_backlog_database_cli.py
tests/behavior/test_backlog_targeted_epic_creation.py
tests/behavior/test_backlog_targeted_mutations.py
tests/behavior/test_backlog_remaining_mutations.py
docs/architecture/canonical-backlog-runtime-architecture.md
docs/development/backlog-session-update-plan-2026-07-10.md
```

## Immediate First Task

Verify that the full provider recreation finished cleanly:

```bash
uv run jj backlog reconcile \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --all \
  --dry-run
```

Expected result: zero planned/remaining operations.

Then apply the backlog updates in:

```text
docs/development/backlog-session-update-plan-2026-07-10.md
```

After that, begin the REST pass by inventorying each current application workflow and defining one consistent endpoint/error/confirmation model before adding routes.
