# PostgreSQL Canonical Backlog Persistence

**Status:** Implemented baseline  
**Date:** July 10, 2026  
**Schema:** `johnny_johnny`

## Runtime Role

PostgreSQL is the canonical runtime store for Johnny-Johnny backlog state. YAML is supported only for import, export, backup, migration, and inspection.

Runtime implementation lives in:

```text
src/johnny_johnny_agent/capabilities/backlog_persistence/postgres.py
src/johnny_johnny_agent/capabilities/backlog_persistence/workflow.py
```

## Configuration

Set the connection string in the project-root `.env` file:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/styxcd
```

The application explicitly uses the `johnny_johnny` schema and does not depend on a shell or IDE session's `search_path`.

Do not commit `.env` or credentials.

## Readiness Check

```bash
uv run jj backlog db check
```

The check verifies connectivity, schema availability, the nine canonical tables, and seeded providers.

## Import and Export

```bash
uv run jj backlog db import \
  --file data/input/backlog/backlog-sandbox.yml \
  --dry-run

uv run jj backlog db import \
  --file data/input/backlog/backlog-sandbox.yml \
  --confirm

uv run jj backlog db export \
  --project "Johnny-Johnny Backlog Persistence Sandbox" \
  --output /tmp/backlog-from-db.yml
```

Import replaces one selected project snapshot transactionally. Export reconstructs the canonical domain and writes version-1 YAML.

The sandbox round trip was verified with:

```text
21 epics
198 issues
68 acceptance criteria
25 comments
```

The original and exported documents were semantically identical. YAML mapping-key order changed in provider metadata, which is acceptable because mapping order is not domain data.

## Runtime Command Boundary

Normal backlog commands select a project using:

```text
provider / provider account username / provider project title
```

The selected database row supplies the provider binding, including the GitHub ProjectV2 external ID. The title is a database lookup key; commands do not implicitly rebind the record to another GitHub project with the same or supplied name.

## Development Network Exception

The July 10 sandbox validation temporarily exposed PostgreSQL directly for disposable development data. This is an environment exception, not the target architecture.

When Johnny-Johnny moves into its AWS server deployment:

- remove public `5432` access
- use private networking/security-group-to-security-group access
- rotate the temporary credential
- require appropriately verified TLS

## Historical Prototype Scripts

The Python scripts in this directory were design prototypes. The supported runtime interfaces are now the `jj backlog db` commands and the `backlog_persistence` package.
