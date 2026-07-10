import pytest

import johnny_johnny_agent.capabilities.backlog_persistence.workflow as workflow
from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue, Project


class FakeTransaction:
    def __init__(self, backlog, events, *, save_error=None):
        self.backlog = backlog
        self.events = events
        self.save_error = save_error

    def __enter__(self):
        self.events.append("transaction:begin")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.events.append("transaction:commit" if exc_type is None else "transaction:rollback")
        return False

    def load_backlog(self, location, *, lock_project=False):
        self.events.append(f"database:load:lock={lock_project}")
        return self.backlog

    def insert_issue(self, location, parent_epic_id, issue):
        self.events.append(f"database:insert-issue:{parent_epic_id}:{issue.id}")

    def save_item(self, location, item, *, parent_epic_id=None):
        self.events.append(f"database:save:{parent_epic_id}:{item.id}")
        if self.save_error:
            raise self.save_error


class FakeRepository:
    def __init__(self, transaction):
        self._transaction = transaction

    def transaction(self):
        return self._transaction


def test_create_issue_commits_after_github_projection(monkeypatch):
    events = []
    backlog = _backlog(include_issue=False)
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, transaction)
    parent_row = _live_parent("source-epic", "I_source", 101, "PVTI_source")

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [parent_row])
    monkeypatch.setattr(workflow, "get_repository", lambda owner, name: {"id": "R_test"})

    def create_github_issue(**kwargs):
        events.append("github:create-issue")
        return {
            "id": "I_child",
            "databaseId": 303,
            "number": 303,
            "title": kwargs["title"],
            "body": kwargs["body"],
            "url": "https://github.test/issues/303",
        }

    monkeypatch.setattr(workflow, "create_github_issue", create_github_issue)
    monkeypatch.setattr(
        workflow,
        "add_issue_to_project",
        lambda project_id, issue_id: events.append("github:add-project") or {"id": "PVTI_child"},
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append("github:update-status") or {"id": "PVTI_child"},
    )
    monkeypatch.setattr(workflow, "get_github_issue_parent", lambda issue_id: None)
    monkeypatch.setattr(
        workflow,
        "add_sub_issue",
        lambda **kwargs: events.append(f"github:add-parent:replace={kwargs['replace_parent']}") or {},
    )
    monkeypatch.setattr(
        workflow,
        "update_github_issue",
        lambda *args, **kwargs: pytest.fail("new issue body already matches canonical content"),
    )

    issue, parent = workflow.create_issue_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        parent_epic_id="source-epic",
        title="New Child",
        issue_id="new-child",
        description="Created directly.",
        acceptance_criteria=["Both sides agree."],
        database_url="postgresql://example.test/db",
    )

    assert parent.id == "source-epic"
    assert issue.provider_metadata["github"]["issue_id"] == "I_child"
    assert events == [
        "transaction:begin",
        "database:load:lock=True",
        "database:insert-issue:source-epic:new-child",
        "github:create-issue",
        "github:add-project",
        "github:update-status",
        "github:add-parent:replace=True",
        "database:save:source-epic:new-child",
        "transaction:commit",
    ]


def test_create_issue_database_failure_deletes_new_github_issue(monkeypatch):
    events = []
    transaction = FakeTransaction(
        _backlog(include_issue=False),
        events,
        save_error=ValueError("database finalization failed"),
    )
    _install_repository(monkeypatch, transaction)
    parent_row = _live_parent("source-epic", "I_source", 101, "PVTI_source")
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [parent_row])
    monkeypatch.setattr(workflow, "get_repository", lambda owner, name: {"id": "R_test"})
    monkeypatch.setattr(
        workflow,
        "create_github_issue",
        lambda **kwargs: {
            "id": "I_child",
            "databaseId": 303,
            "number": 303,
            "title": kwargs["title"],
            "body": kwargs["body"],
            "url": "https://github.test/issues/303",
        },
    )
    monkeypatch.setattr(workflow, "add_issue_to_project", lambda *args: {"id": "PVTI_child"})
    monkeypatch.setattr(workflow, "update_project_item_status", lambda **kwargs: {})
    monkeypatch.setattr(workflow, "get_github_issue_parent", lambda issue_id: None)
    monkeypatch.setattr(workflow, "add_sub_issue", lambda **kwargs: {})
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    with pytest.raises(workflow.BacklogPersistenceError, match="database finalization failed"):
        workflow.create_issue_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            parent_epic_id="source-epic",
            title="New Child",
            issue_id="new-child",
            database_url="postgresql://example.test/db",
        )

    assert events[-2:] == ["transaction:rollback", "github:delete:I_child"]


def test_update_item_commits_content_status_comment_and_database(monkeypatch):
    events = []
    transaction = FakeTransaction(_backlog(include_issue=True), events)
    _install_repository(monkeypatch, transaction)
    rows = [_live_parent("source-epic", "I_source", 101, "PVTI_source"), _live_issue()]
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: rows)

    def update_issue(issue_id, *, title=None, body=None):
        events.append(f"github:update-content:{title}")
        return {**_live_issue(), "title": title, "body": body}

    monkeypatch.setattr(workflow, "update_github_issue", update_issue)
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append(f"github:update-status:{kwargs['status']}") or {},
    )
    monkeypatch.setattr(
        workflow,
        "create_issue_comment",
        lambda **kwargs: events.append("github:create-comment") or {
            "id": "IC_new",
            "databaseId": 44,
            "url": "https://github.test/comments/44",
            "createdAt": "2026-07-10T12:00:00Z",
            "updatedAt": "2026-07-10T12:00:00Z",
        },
    )

    item = workflow.update_item_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        item_id="existing-issue",
        title="Updated Issue",
        description="Updated description.",
        status="in progress",
        acceptance_criteria=["Updated criterion."],
        comment="Updated through the CLI.",
        database_url="postgresql://example.test/db",
    )

    assert item.title == "Updated Issue"
    assert item.status == "In Progress"
    assert item.comments[-1].provider_metadata["github"]["comment_id"] == "IC_new"
    assert events[-1] == "transaction:commit"
    assert "database:save:source-epic:existing-issue" in events


def test_update_database_failure_restores_github(monkeypatch):
    events = []
    transaction = FakeTransaction(
        _backlog(include_issue=True),
        events,
        save_error=ValueError("save failed"),
    )
    _install_repository(monkeypatch, transaction)
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [_live_issue()])

    def update_issue(issue_id, *, title=None, body=None):
        events.append(f"github:update-content:{title}")
        return {**_live_issue(), "title": title, "body": body}

    monkeypatch.setattr(workflow, "update_github_issue", update_issue)
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append(f"github:update-status:{kwargs['status']}") or {},
    )
    monkeypatch.setattr(
        workflow,
        "create_issue_comment",
        lambda **kwargs: {"id": "IC_new", "databaseId": 44, "url": "url"},
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue_comment",
        lambda comment_id: events.append(f"github:delete-comment:{comment_id}"),
    )

    with pytest.raises(workflow.BacklogPersistenceError, match="save failed"):
        workflow.update_item_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            item_id="existing-issue",
            title="Updated Issue",
            status="In Progress",
            comment="Temporary comment.",
            database_url="postgresql://example.test/db",
        )

    assert events[-4:] == [
        "transaction:rollback",
        "github:delete-comment:IC_new",
        "github:update-status:Ready",
        "github:update-content:Existing Issue",
    ]


def test_move_issue_replaces_parent_and_commits(monkeypatch):
    events = []
    transaction = FakeTransaction(_backlog(include_issue=True), events)
    _install_repository(monkeypatch, transaction)
    rows = [
        _live_parent("source-epic", "I_source", 101, "PVTI_source"),
        _live_parent("target-epic", "I_target", 202, "PVTI_target", repository="ggortsema/target-repo"),
        _live_issue(),
    ]
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: rows)
    monkeypatch.setattr(
        workflow,
        "get_github_issue_parent",
        lambda issue_id: {
            "id": "I_source",
            "databaseId": 101,
            "number": 101,
            "repository": {"nameWithOwner": "ggortsema/test-repo"},
        },
    )
    monkeypatch.setattr(
        workflow,
        "add_sub_issue",
        lambda **kwargs: events.append(
            f"github:parent:{kwargs['parent_issue_number']}:replace={kwargs['replace_parent']}"
        ) or {},
    )
    monkeypatch.setattr(
        workflow,
        "update_github_issue",
        lambda issue_id, **kwargs: events.append("github:update-parent-body") or {
            **_live_issue(),
            "body": kwargs["body"],
        },
    )

    issue, source, target = workflow.move_issue_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        issue_id="existing-issue",
        target_epic_id="target-epic",
        database_url="postgresql://example.test/db",
    )

    assert source.id == "source-epic"
    assert target.id == "target-epic"
    assert issue.order == 1000
    assert issue.repository == "ggortsema/test-repo"
    assert issue.milestone is None
    assert "github:parent:202:replace=True" in events
    assert events[-2:] == ["database:save:target-epic:existing-issue", "transaction:commit"]


def _install_repository(monkeypatch, transaction):
    monkeypatch.setattr(
        workflow,
        "PostgresBacklogRepository",
        lambda database_url: FakeRepository(transaction),
    )


def _backlog(*, include_issue):
    source = Epic(
        id="source-epic",
        type="epic",
        title="Source Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=1000,
        provider_metadata={"github": {"issue_id": "I_source", "number": 101}},
    )
    target = Epic(
        id="target-epic",
        type="epic",
        title="Target Epic",
        repository="ggortsema/target-repo",
        status="Backlog",
        issue_state="OPEN",
        order=2000,
        milestone="Target Milestone",
        provider_metadata={"github": {"issue_id": "I_target", "number": 202}},
    )
    if include_issue:
        source.issues.append(
            Issue(
                id="existing-issue",
                type="issue",
                title="Existing Issue",
                repository="ggortsema/test-repo",
                status="Ready",
                issue_state="OPEN",
                order=1000,
                description="Existing description.",
                acceptance_criteria=["Existing criterion."],
                provider_metadata={
                    "github": {
                        "issue_id": "I_child",
                        "database_id": 303,
                        "number": 303,
                        "url": "https://github.test/issues/303",
                        "project_item_id": "PVTI_child",
                    }
                },
            )
        )
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            provider_metadata={"github": {"project_id": "PVT_test"}},
        ),
        epics=[source, target],
    )


def _live_parent(
    canonical_id,
    issue_id,
    number,
    project_item_id,
    *,
    repository="ggortsema/test-repo",
):
    return {
        "id": issue_id,
        "databaseId": number,
        "database_id": number,
        "number": number,
        "title": f"[Epic] {canonical_id}",
        "body": (
            "<!-- johnny-johnny\n"
            f"id: {canonical_id}\n"
            "schema: backlog-v1\n"
            "type: epic\n"
            "-->"
        ),
        "url": f"https://github.test/issues/{number}",
        "repository": repository,
        "project_item_id": project_item_id,
        "project_status": "Backlog",
    }


def _live_issue():
    return {
        "id": "I_child",
        "databaseId": 303,
        "database_id": 303,
        "number": 303,
        "title": "Existing Issue",
        "body": (
            "<!-- johnny-johnny\n"
            "id: existing-issue\n"
            "schema: backlog-v1\n"
            "type: issue\n"
            "parent: source-epic\n"
            "-->\n\nExisting description.\n\n## Acceptance Criteria\n\n"
            "- [ ] Existing criterion."
        ),
        "url": "https://github.test/issues/303",
        "repository": "ggortsema/test-repo",
        "project_item_id": "PVTI_child",
        "project_status": "Ready",
    }
