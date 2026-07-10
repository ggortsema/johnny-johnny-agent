# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for Johnny-Johnny, a personal engineering assistant built around deterministic, reusable engineering workflows.

The same capabilities are intended to be reusable from CLI, FastAPI, chat, webhooks, and future UI adapters.

## Current Architecture

```text
CLI today ───────────┐
REST API next ───────┼── application workflows ── canonical domain
webhooks later ──────┘            │
                                  ├── PostgreSQL canonical store
                                  └── provider adapters (GitHub first)
```

PostgreSQL is the canonical runtime store for backlog state. GitHub Projects are provider projections. YAML is a portable import/export, migration, backup, validation, and inspection format—not a runtime intermediary.

Stable Johnny-Johnny IDs are canonical identity. GitHub issue numbers, node IDs, URLs, and project-item IDs are provider metadata.

## Configuration

Place the PostgreSQL connection string in the project-root `.env` file:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
```

Then install/synchronize dependencies and verify persistence:

```bash
uv sync
uv run jj backlog db check
```

## PostgreSQL-Backed Reads

```bash
uv run jj backlog inspect --project "PROJECT"
uv run jj backlog list epics --project "PROJECT"
uv run jj backlog list items --project "PROJECT"
uv run jj backlog describe ITEM_ID --project "PROJECT"
```

List and describe commands support their documented human, YAML, and JSON output formats. YAML output is rendering only.

## Targeted Mutations

```bash
uv run jj backlog create epic ... --project "PROJECT" --dry-run
uv run jj backlog create epic ... --project "PROJECT" --confirm

uv run jj backlog create issue ... --project "PROJECT" --dry-run
uv run jj backlog create issue ... --project "PROJECT" --confirm

uv run jj backlog update ITEM_ID ... --project "PROJECT" --dry-run
uv run jj backlog update ITEM_ID ... --project "PROJECT" --confirm

uv run jj backlog move ISSUE_ID --to-epic EPIC_ID --project "PROJECT" --dry-run
uv run jj backlog move ISSUE_ID --to-epic EPIC_ID --project "PROJECT" --confirm

uv run jj maintenance delete-issue ISSUE_ID --project "PROJECT" --dry-run
uv run jj maintenance delete-issue ISSUE_ID --project "PROJECT" --confirm
```

Confirmed mutations write PostgreSQL and synchronize the targeted GitHub projection before reporting success. Workflows use rollback, compensation, and idempotent repair because PostgreSQL and GitHub cannot share one transaction.

## Reconcile and Purge

```bash
uv run jj backlog reconcile --project "PROJECT" --max-operations 100 --dry-run
uv run jj backlog reconcile --project "PROJECT" --all --confirm

uv run jj maintenance purge --project "PROJECT" --max-issues 50 --dry-run
uv run jj maintenance purge --project "PROJECT" --all --confirm
```

Reconcile reads PostgreSQL and applies the provider plan. Purge removes the GitHub projection while preserving canonical PostgreSQL rows.

## YAML Utilities

```bash
uv run jj backlog validate --file backlog.yml
uv run jj backlog db import --file backlog.yml --dry-run
uv run jj backlog db import --file backlog.yml --confirm
uv run jj backlog db export --project "PROJECT" --output backlog.yml
```

`jj backlog pull` remains a raw GitHub diagnostic.

`jj backlog generate` remains temporarily as a GitHub-to-YAML migration utility and is explicitly deferred for replacement by a direct GitHub-to-PostgreSQL import workflow.

Removed legacy commands:

```text
jj backlog publish
jj backlog preview-epic-body
```

## API

```bash
uv run jj serve
```

The current FastAPI app exposes only a minimal hello endpoint. The next implementation story is to expose the PostgreSQL-backed application workflows through typed REST endpoints without invoking the CLI.

## Documentation

Start with:

- `docs/architecture/canonical-backlog-runtime-architecture.md`
- `docs/architecture/adrs/ADR-001-postgresql-canonical-backlog-runtime.md`
- `docs/architecture/adrs/ADR-002-targeted-provider-synchronization.md`
- `docs/database/postgres/README.md`
- `docs/specifications/backlog-v1.md`
- `docs/development/ENGINEERING_PRINCIPLES.md`
- `docs/development/WORKING_AGREEMENT.md`
