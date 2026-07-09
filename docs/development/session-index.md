# Session Index

**Date:** July 9, 2026

**Project:** Johnny-Johnny Agent

**Project Version:** 0.1.0

**Git Branch:** dev

**Current Story:** synchronize-canonical-comments-to-provider-projection

**Next Story:** implement-postgres-backed-canonical-backlog-persistence

**Important Carryover:** Reconciliation is functionally improved, but large destructive full-project recreates now exceed or appear to exceed GitHub content-generation limits. Decide and implement a safer reconcile execution strategy before relying on full production purge/recreate.

---

## Session Summary

This session continued the Johnny-Johnny engineering work after pausing PostgreSQL-backed canonical persistence.

The immediate goal was to make canonical backlog reconciliation complete enough to safely recreate a GitHub Project projection from `backlog.yml`. The blocker was that canonical comments existed in YAML but were not written to GitHub. During validation, we also found that acceptance criteria were not rendered into GitHub issue bodies, newly created project items were not assigned canonical statuses, and destructive full-project recreate can hit GitHub content-generation throttling.

The session made major progress:

- Canonical comments are now planned and written as GitHub issue comments.
- GitHub issue comments use hidden Johnny-Johnny metadata.
- Reconcile reads provider-side comments back from GitHub.
- Comment metadata is hydrated into YAML.
- Acceptance criteria are now rendered as GitHub checkbox lists when present in YAML.
- Newly created project items are planned for status updates.
- Sandbox validation confirmed comments, acceptance criteria, and statuses work for representative items.
- The remaining blocker is not core mapping behavior; it is safe execution strategy for large GitHub mutation batches.

The user wants the next session to resume PostgreSQL-backed canonical persistence work, while preserving a clear note that reconcile still needs chunking/backoff/resume/budget strategy before production-scale destructive recreation is safe.

---

## Major Outcomes

### 1. Reconcile Comments Implemented

Before this session, comments were part of the domain model and YAML model, but not part of provider reconciliation.

Existing model support:

- `Comment` domain object existed.
- `Issue.comments` and `Epic.comments` existed.
- YAML loader loaded comments.
- YAML writer saved comments.
- `jj backlog update --comment` appended canonical comments.

Gap:

- Planner never emitted comment operations.
- Executor never wrote comments to GitHub.
- GitHub client did not create issue comments.
- Provider comment metadata was not hydrated.

Implemented direction:

- Added `CreateCommentOperation`.
- Planner now detects canonical comments missing from provider projection.
- Executor writes missing comments to GitHub.
- GitHub comment bodies include Johnny-Johnny metadata.
- GitHub client reads comments under each projected issue.
- Reconcile hydrates `comment.provider_metadata.github`.
- Repeated reconcile should not duplicate comments once provider comments can be read.

Representative successful manual validation:

- `Add End-to-End CLI Behavior Tests` had three planned comments.
- `Expand Update Issue Command` had two comments.
- `Complete Canonical CLI Grammar` had two comments.
- `Record Provider Reconciliation State` was confirmed to have comments in GitHub.

---

## 2. Acceptance Criteria Rendering Implemented

A second projection gap was found during manual GitHub inspection.

`renderer.py` previously rendered only:

```text
hidden johnny-johnny metadata
description
```

It did not render `acceptance_criteria`.

Fix:

- `render_epic_body(...)` now passes acceptance criteria.
- `render_issue_body(...)` now passes acceptance criteria.
- `_render_body(...)` renders formal YAML acceptance criteria as GitHub checkboxes:

```markdown
## Acceptance Criteria

- [ ] Criterion text
```

Manual validation:

- `Record Provider Reconciliation State` has both acceptance criteria and comments.
- GitHub showed acceptance criteria as checkboxes.
- This confirmed the renderer path works when formal YAML `acceptance_criteria` exist.

Important data-quality discovery:

- Many older backlog stories do not have formal `acceptance_criteria`; acceptance-like content exists in their description bodies.
- Example: `Expand Update Issue Command` has comments but no formal `acceptance_criteria`.
- This is not a renderer bug; it reflects older backlog data shape.

---

## 3. Status Updates For Newly Created Items Added

A status projection gap was found.

Before this session:

- Existing live issues could get status updates.
- Newly created issues were created, added to the project, attached to their epic, and then skipped.
- Planner did not emit `UpdateIssueStatusOperation` for newly created items.

Fix direction:

- Planner now emits `UpdateIssueStatusOperation` after creating/adding new epics/issues.
- Executor already knew how to call `update_project_item_status(...)`.
- For epics, `CreateEpicOperation` adds the epic issue to the project immediately, so status can be set after epic creation.
- For issues, planner order should be:

```text
CreateIssueOperation
AddIssueToProjectOperation
UpdateIssueStatusOperation
AttachIssueToEpicOperation
CreateCommentOperation(s)
```

Important provider setup issue:

- GitHub Projects created from the default template may only have Status options:

```text
Todo
In Progress
Done
```

- Current code expected:

```text
Backlog
Ready
In progress
In review
Done
```

or, if mapping was later changed, title-case:

```text
Backlog
Ready
In Progress
In Review
Done
```

- The sandbox initially failed because its Status field did not contain `Backlog`.
- User likely created the sandbox without the prior template that had the correct Status options.
- This led to a clear future need: provider project schema preflight before any mutation.

---

## 4. Sandbox Validation Status

The sandbox project was purged/recreated multiple times.

Sandbox project:

```text
Johnny-Johnny Backlog Persistence Sandbox
```

Sandbox YAML:

```text
data/input/backlog/backlog-sandbox.yml
```

Sandbox state at session close:

- User reports the sandbox is populated with all but one story.
- Comments were confirmed present in GitHub.
- `Record Provider Reconciliation State` was confirmed to show:
  - acceptance criteria as checkboxes
  - comments as GitHub comments
- Status behavior appeared to work after project Status options were corrected.

Known caveat:

- The sandbox may not be a perfect full projection due to the final GitHub content-generation throttling issue and/or one missing story.
- It remains safe for DB experimentation and further provider-sync testing.
- The sandbox can be purged if needed.

---

## 5. Production/Main Projection Attempt Hit GitHub Content-Generation Limit

After sandbox validation, we attempted to purge/recreate the production/main GitHub Project projection:

```text
MycroftAI Engineering Roadmap
```

Production commands discussed:

```bash
cp data/input/backlog/backlog.yml data/input/backlog/backlog.before-main-recreate.yml

jj maintenance purge   --project "MycroftAI Engineering Roadmap"   --confirm

jj backlog reconcile   --file data/input/backlog/backlog.yml   --confirm
```

Failure observed during main reconcile:

```text
Creating issue: Implement Secrets Management Strategy
AttributeError: 'NoneType' object has no attribute 'get'
```

Root cause in code:

```python
issue = create_issue(...)
_hydrate_github_metadata(item=issue_model, issue=issue)
```

`create_issue(...)` returned `None`, and executor assumed it was always a dict.

Guard added/recommended for `client.py`:

```python
def create_issue(repository_id: str, title: str, body: str = "") -> dict:
    mutation = """
    mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
      createIssue(input: {
        repositoryId: $repositoryId
        title: $title
        body: $body
      }) {
        issue {
          id
          databaseId
          number
          title
          url
        }
      }
    }
    """

    data = execute_graphql(
        mutation,
        {
            "repositoryId": repository_id,
            "title": title,
            "body": body,
        },
    )

    create_issue_result = data.get("createIssue")
    if not create_issue_result:
        raise RuntimeError(
            f"GitHub createIssue returned no createIssue payload for title: {title}"
        )

    issue = create_issue_result.get("issue")
    if not issue:
        raise RuntimeError(
            f"GitHub createIssue returned no issue payload for title: {title}. "
            f"Response payload: {create_issue_result}"
        )

    return issue
```

After adding the guard, retry failed immediately on the first create:

```text
Creating epic: [Epic] GKE Workflow
RuntimeError: GitHub createIssue returned no issue payload for title: [Epic] GKE Workflow. Response payload: {'issue': None}
```

Interpretation:

- This is very likely GitHub content-generation throttling / secondary rate limiting.
- It failed after a partial run, then immediately failed on the first create on retry.
- The full destructive recreate now performs many more content mutations than before:

```text
create issue
add to project
update status
attach sub-issue
create comments
```

- A large backlog can exceed practical GitHub mutation limits quickly.
- This is not considered a blocker for starting DB work, but it is a blocker for declaring production destructive recreate safe.

Important final user assessment:

> It is not the end of the world. We have all the stories captured, we are pretty sure it will work, and we have the sandbox populated with all but one of the stories.

---

## 6. Reconcile Execution Strategy Still Needed

Before production-grade full reconcile/recreate, decide and implement one of these strategies:

### Option A: Chunked Reconcile

Add a CLI option such as:

```bash
jj backlog reconcile --file data/input/backlog/backlog.yml --confirm --max-operations 100
```

Behavior:

- Execute only the first N operations.
- Save hydrated YAML after the chunk.
- User can rerun until complete.
- This is likely the simplest near-term fix.

### Option B: Mutation Budgeting

Classify operations as content-generating GitHub mutations and stop before known provider limits.

Example:

```text
max_content_mutations_per_run = 100
```

### Option C: Retry/Backoff

Wrap GitHub mutations with retry/backoff when GitHub returns null/secondary limit symptoms.

This is useful, but it does not solve a hard 500/hour content-generation ceiling by itself.

### Option D: Resume-Safe Reconcile

Make reconcile resumable and durable:

- Save after each operation or small batch.
- Recalculate plan from provider state on each run.
- Avoid losing progress when one provider call fails.

### Option E: Reduce Mutations

Potential optimizations:

- Do not update status when provider default already matches.
- Delay comments until base issue graph exists.
- Bulk or staged workflows if provider supports them.
- Separate creation pass from decoration pass.

### Immediate Recommendation

Implement **chunked/resumable reconcile** first.

A practical first version:

```text
--max-operations N
save YAML after execution
exit cleanly after N operations
rerun reconcile until complete
```

This would let large recreates work within GitHub limits and make failures less destructive.

---

## 7. Future Workspace / Anchor Repo Direction

A design direction emerged:

Do not continue using `styxcd-docs` as the long-term issue host for every projection.

Future model:

```text
Johnny-Johnny Workspace
  canonical/project settings
  provider settings
  GitHub ProjectV2
  GitHub anchor repository
  saved views
  status/workflow field options
  provider projection metadata
```

For GitHub:

- Create a dedicated anchor repo per workspace.
- Create/recreate the GitHub Project.
- Apply saved fields/status options/views.
- Reconcile backlog into that anchor repo/project.
- On purge/recreate, delete/recreate the anchor repo too.

Benefits:

- Stops polluting `styxcd-docs`.
- Resets issue numbers per workspace.
- Makes provider projection infrastructure disposable.
- Avoids hand-created project template drift.
- Supports reproducible sandbox/prod environments.

This is not for the next DB session unless needed, but it should be remembered as the future direction.

---

## 8. Important Domain Model Reflection

A major design insight emerged around “canonical” backlog state.

Initial assumption:

```text
Canonical backlog item owns all state.
Providers are projections.
```

Refined understanding:

```text
Canonical identity and intent are stable.
Provider projections may own provider-native workflow state once active.
```

Why:

- If the same backlog is in GitHub and Jira, statuses can diverge.
- Comments may have different provider IDs, timestamps, authorship, and edit history.
- If a team works in Jira after migration, Jira may become the active owner of workflow state.
- Johnny-Johnny should track identity, mappings, drift, and reconciliation history, not naively force every provider field into one canonical row forever.

Likely future model:

```text
backlog_item
  stable identity / intent

provider_backlog_item
  provider
  provider item id
  provider status
  provider timestamps
  active/inactive
  sync policy
  last reconciled state

workspace_provider_projection
  provider
  project/repo/board metadata
  active authority mode
```

Key principle:

```text
Canonical does not mean Johnny-Johnny owns every field forever.
Canonical means Johnny-Johnny preserves stable identity, intent, continuity, and reconciliation knowledge.
```

This matters for the upcoming database work.

---

## Files Changed Or Likely Changed This Session

Expected modified files:

```text
src/johnny_johnny_agent/capabilities/backlog_sync/planner.py
src/johnny_johnny_agent/capabilities/backlog_sync/executor.py
src/johnny_johnny_agent/capabilities/github/client.py
src/johnny_johnny_agent/capabilities/github/renderer.py
src/johnny_johnny_agent/cli/main.py
tests/behavior/test_backlog_reconcile_comments.py
data/input/backlog/backlog.yml
data/input/backlog/backlog-sandbox.yml
```

Possibly changed:

```text
data/input/backlog/backlog.before-main-recreate.yml
```

Previously completed DB files:

```text
docs/database/postgres/001_create_canonical_backlog_tables.sql
docs/database/postgres/002_seed_core_providers.sql
```

---

## Tests / Validation Performed

User reported:

```text
22 tests passed
```

This was after adding the comment reconciliation tests and implementation.

Recommended before commit/merge/tag:

```bash
uv run python -m compileall src/johnny_johnny_agent
uv run pytest
```

Also inspect git diff carefully:

```bash
git diff
git status
```

---

## Git / Release State

User is on:

```text
dev
```

User intended to:

```text
commit code
merge dev to main
tag
```

But then main reconcile failed due GitHub createIssue returning null.

Recommendation:

1. Commit current code on `dev` after tests pass.
2. Do **not** tag as “production reconcile fully validated.”
3. Either:
   - tag as a pre-DB checkpoint with known GitHub mutation-limit caveat, or
   - wait until chunked/resumable reconcile is implemented.
4. If merging to main, include the caveat in commit message or release note.

Possible tag name if user still wants a checkpoint:

```text
pre-db-reconcile-comments
```

or:

```text
pre-db-reconcile-comments-sandbox-validated
```

Avoid tag names implying full production recreate safety unless chunking/backoff is implemented.

---

## Current Main/Production Projection Caveat

Do not assume `MycroftAI Engineering Roadmap` is fully recreated.

The main projection may be:

- partially purged
- partially recreated
- empty
- missing recently attempted items
- blocked by GitHub secondary/content-generation throttling

Before doing anything destructive next session, inspect actual GitHub state or run a dry-run once GitHub limits cool down.

Recommended cautious command later:

```bash
jj backlog reconcile   --file data/input/backlog/backlog.yml   --dry-run
```

But do not immediately run `--confirm` repeatedly if GitHub is still returning null issue payloads.

---

## PostgreSQL Work Already Completed Before This Session

Database access path:

```text
DB tool: DBTable / IntelliJ database tooling
Connection: PostgreSQL over SSH tunnel
SSH user: ec2-user
SSH server: orchestrator.styxcd.com
Database: styxcd
PostgreSQL user: rincexwind
```

Dedicated schema:

```sql
CREATE SCHEMA johnny_johnny AUTHORIZATION rincexwind;
```

Important schema setup:

```sql
BEGIN;

SET search_path TO johnny_johnny;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

`pgcrypto` required installing:

```bash
sudo dnf install -y postgresql15-contrib
```

Tables created:

```text
johnny_johnny.backlog_item_acceptance_criteria
johnny_johnny.backlog_item_assignees
johnny_johnny.backlog_item_comments
johnny_johnny.backlog_item_labels
johnny_johnny.backlog_items
johnny_johnny.provider_accounts
johnny_johnny.provider_projects
johnny_johnny.providers
johnny_johnny.users
```

Seeded providers include:

```text
github
jira
linear
gitlab
local
```

Verification query:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'johnny_johnny'
ORDER BY table_name;
```

---

## Recommended First Task Next Session

Start DB work, but keep reconcile mutation strategy in the backlog.

First next-session prompt:

```text
We are resuming Johnny-Johnny DB work. Reconcile comments, acceptance rendering, and status setting were validated in sandbox, but production-scale destructive recreate hit GitHub content-generation limits. Start PostgreSQL-backed canonical persistence using the existing johnny_johnny schema, but keep a follow-up note that reconcile needs chunking/resume/backoff before production recreate is safe.
```

Immediate first task:

```text
Inspect the current domain model, YAML loader/writer, and postgres schema to design the first importer/exporter path between backlog.yml and johnny_johnny tables.
```

Likely files needed next:

```text
src/johnny_johnny_agent/domain/backlog.py
src/johnny_johnny_agent/capabilities/backlog_sync/yaml_loader.py
src/johnny_johnny_agent/capabilities/backlog_sync/yaml_writer.py
src/johnny_johnny_agent/cli/main.py
docs/database/postgres/001_create_canonical_backlog_tables.sql
docs/database/postgres/002_seed_core_providers.sql
data/input/backlog/backlog.yml
data/input/backlog/backlog-sandbox.yml
tests/behavior/test_backlog_cli_workflows.py
tests/behavior/test_backlog_reconcile_comments.py
```

DB implementation likely needs new files such as:

```text
src/johnny_johnny_agent/capabilities/backlog_persistence/__init__.py
src/johnny_johnny_agent/capabilities/backlog_persistence/postgres.py
src/johnny_johnny_agent/capabilities/backlog_persistence/importer.py
src/johnny_johnny_agent/capabilities/backlog_persistence/exporter.py
tests/behavior/test_backlog_postgres_persistence.py
```

Potential CLI commands:

```text
jj backlog db import --file data/input/backlog/backlog-sandbox.yml --confirm
jj backlog db export --output data/input/backlog/backlog-from-db.yml
```

or:

```text
jj backlog persistence import
jj backlog persistence export
```

Decide naming before implementation.

---

## Working Style Reminder

The user prefers:

- one meaningful change at a time
- complete file replacements for new/small files
- complete method/function/import-block replacements for large files
- avoid tiny inline surgery when indentation is risky
- tests after meaningful changes
- explicit commands
- no more hidden assumptions around provider behavior
- durable session handoffs named exactly `session-index.md`

---

## Final Session Takeaway

The reconciliation workflow is substantially better:

```text
canonical comments -> GitHub comments
acceptance criteria -> GitHub checkboxes
canonical statuses -> GitHub Project Status field
provider metadata -> hydrated YAML
```

The remaining issue is execution safety at scale against GitHub:

```text
large destructive recreate -> too many content-generating mutations -> createIssue returns null
```

This is a provider-limit/execution-strategy problem, not a failure of the canonical comment/acceptance/status projection model itself.

Next session can resume DB work, with the explicit understanding that reconcile needs chunking/resume/backoff before production-scale recreate is considered safe.
