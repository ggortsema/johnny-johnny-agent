# Decision Log

Version: 1.0

Purpose:
Capture important engineering and workflow decisions that are too small for an ADR but too valuable to lose.

## Template

Date:
Decision:
Reason:
Supersedes:
Related Story:

---

## 2026-07-08

Decision:
Replace complete methods/functions instead of whole files during AI collaboration.

Reason:
Files have grown large while complete method replacement remains safe and reviewable.

---

## 2026-07-08

Decision:
List commands use a shared table format.

Reason:
Provides a consistent CLI experience.

---

## 2026-07-08

Decision:
Support include and exclude filtering.

Reason:
Common workflow is 'show me everything except Done.'
---

## 2026-07-10

Decision:
Remove the legacy `jj backlog publish` Markdown-to-GitHub workflow. Keep `jj backlog pull` as a provider diagnostic. Defer `jj backlog generate` migration and rename until durable, rate-limited provider reconciliation is implemented; its future replacement will import a GitHub Project directly into PostgreSQL without using YAML as an intermediary.

Reason:
`publish` bypassed the canonical PostgreSQL model and the current reconciliation workflow. Migrating `generate` now would couple provider import to the same large-mutation reliability problem already captured by the durable reconciliation ADR.

Related Story:
implement-postgres-backed-canonical-backlog-persistence

---

## 2026-07-10 — PostgreSQL Runtime Canonical State

Decision:
Use PostgreSQL as the canonical runtime backlog store. Keep YAML only for import, export, backup, migration, validation, and human inspection. Migrated commands must not use YAML as an intermediary.

Reason:
Server mode, REST, webhooks, concurrency, audit history, and multiple provider projections require durable transactional state.

Related ADR:
`ADR-001-postgresql-canonical-backlog-runtime.md`

---

## 2026-07-10 — Intentional Breaking CLI Migration

Decision:
Replace YAML-backed commands one at a time rather than preserving parallel legacy commands. Runtime commands select canonical projects from PostgreSQL using provider, provider account, and stored project title.

Reason:
Parallel persistence paths would create ambiguous behavior and ongoing compatibility cost.

---

## 2026-07-10 — Targeted Provider Synchronization

Decision:
Confirmed create, update, move, and delete workflows must synchronize the targeted GitHub projection before reporting success. Use PostgreSQL rollback, provider compensation, idempotent retry, and explicit consistency errors because GitHub and PostgreSQL cannot share an ACID transaction.

Reason:
Users expect CLI/API mutations to appear in GitHub immediately, but a full-project reconcile is unnecessary and can trigger provider limits.

Related ADR:
`ADR-002-targeted-provider-synchronization.md`

---

## 2026-07-10 — Explicit Provider Project Binding

Decision:
`--project` selects the stored `provider_projects` row. Reconcile and targeted mutations use the external provider ID stored on that row and never silently rebind by searching GitHub project titles.

Reason:
Implicit rebinding caused a sandbox epic to be added to the wrong GitHub Project when copied metadata referenced the production project.

---

## 2026-07-10 — Bounded and Full Projection Operations

Decision:
Support both safe bounded execution and explicit `--all` execution for reconcile and purge. Reconcile budgets provider operations; purge budgets issues.

Reason:
Bounded execution protects against provider limits, while `--all` supports unattended or disposable-environment workflows without requiring manual babysitting.

