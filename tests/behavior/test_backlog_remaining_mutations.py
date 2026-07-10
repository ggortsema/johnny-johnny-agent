import pytest

import johnny_johnny_agent.capabilities.backlog_persistence.workflow as workflow
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    CreateCommentOperation,
    CreateIssueOperation,
    ExecutionPlan,
    UpdateIssueStatusOperation,
)
from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue, Project


class FakeTransaction:
    def __init__(self, backlog, events, *, delete_error=None, save_error=None, clear_count=0, clear_error=None):
        self.backlog = backlog
        self.events = events
        self.delete_error = delete_error
        self.save_error = save_error
        self.clear_count = clear_count
        self.clear_error = clear_error

    def __enter__(self):
        self.events.append("transaction:begin")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.events.append("transaction:commit" if exc_type is None else "transaction:rollback")
        return False

    def load_backlog(self, location, *, lock_project=False):
        self.events.append(f"database:load:lock={lock_project}")
        return self.backlog

    def delete_issue(self, location, issue_id):
        self.events.append(f"database:delete:{issue_id}")
        if self.delete_error:
            raise self.delete_error

    def save_item(self, location, item, *, parent_epic_id=None):
        self.events.append(f"database:save:{parent_epic_id}:{item.id}")
        if self.save_error:
            raise self.save_error

    def clear_provider_projection_metadata(self, location, provider):
        self.events.append(f"database:clear-provider:{provider}")
        if self.clear_error:
            raise self.clear_error
        return self.clear_count


class FakeRepository:
    def __init__(self, backlog, transaction):
        self.backlog = backlog
        self._transaction = transaction

    def load(self, location):
        return self.backlog

    def transaction(self):
        return self._transaction


def _install_repository(monkeypatch, backlog, transaction):
    monkeypatch.setattr(
        workflow,
        "PostgresBacklogRepository",
        lambda database_url: FakeRepository(backlog, transaction),
    )


def _backlog():
    issue = Issue(
        id="test-issue",
        type="issue",
        title="Test Issue",
        repository="ggortsema/test-repo",
        status="Ready",
        issue_state="OPEN",
        order=1000,
        comments=[Comment(id="comment-1", body="Test comment")],
        provider_metadata={
            "github": {
                "issue_id": "I_issue",
                "database_id": 22,
                "number": 22,
                "url": "https://github.test/issues/22",
                "project_item_id": "PVTI_issue",
            }
        },
    )
    epic = Epic(
        id="test-epic",
        type="epic",
        title="Test Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=1000,
        issues=[issue],
        provider_metadata={
            "github": {
                "issue_id": "I_epic",
                "database_id": 11,
                "number": 11,
                "url": "https://github.test/issues/11",
                "project_item_id": "PVTI_epic",
            }
        },
    )
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            provider_metadata={"github": {"project_id": "PVT_test"}},
        ),
        epics=[epic],
    )


def _live(canonical_id, issue_id, number, item_type="issue"):
    return {
        "id": issue_id,
        "databaseId": number,
        "number": number,
        "title": canonical_id,
        "body": (
            "<!-- johnny-johnny\n"
            f"id: {canonical_id}\n"
            "schema: backlog-v1\n"
            f"type: {item_type}\n"
            "-->"
        ),
        "url": f"https://github.test/issues/{number}",
        "repository": "ggortsema/test-repo",
        "project_item_id": f"PVTI_{number}",
        "project_status": "Backlog",
        "comments": [],
    }


def test_delete_issue_deletes_provider_then_canonical_and_commits(monkeypatch):
    events = []
    backlog = _backlog()
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(workflow, "get_github_issue", lambda issue_id: {"id": issue_id})
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    result = workflow.delete_issue_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        issue_id="test-issue",
        database_url="postgresql://example.test/db",
    )

    assert result.github_issue_deleted is True
    assert events == [
        "transaction:begin",
        "database:load:lock=True",
        "github:delete:I_issue",
        "database:delete:test-issue",
        "transaction:commit",
    ]


def test_delete_issue_retry_finishes_database_when_provider_is_already_absent(monkeypatch):
    events = []
    backlog = _backlog()
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(
        workflow,
        "get_github_issue",
        lambda issue_id: (_ for _ in ()).throw(RuntimeError(f"GitHub issue not found: {issue_id}")),
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: pytest.fail("already absent provider issue must not be deleted again"),
    )

    result = workflow.delete_issue_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        issue_id="test-issue",
        database_url="postgresql://example.test/db",
    )

    assert result.github_issue_deleted is False
    assert "database:delete:test-issue" in events
    assert events[-1] == "transaction:commit"


def test_delete_issue_reports_retryable_consistency_error_after_database_failure(monkeypatch):
    events = []
    backlog = _backlog()
    transaction = FakeTransaction(backlog, events, delete_error=ValueError("delete failed"))
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(workflow, "get_github_issue", lambda issue_id: {"id": issue_id})
    monkeypatch.setattr(workflow, "delete_github_issue", lambda issue_id: events.append("github:deleted"))

    with pytest.raises(workflow.TargetedBacklogMutationConsistencyError, match="Rerun"):
        workflow.delete_issue_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            issue_id="test-issue",
            database_url="postgresql://example.test/db",
        )

    assert events[-1] == "transaction:rollback"


def test_bounded_reconcile_never_splits_one_item_group():
    backlog = _backlog()
    issue = backlog.epics[0].issues[0]
    plan = ExecutionPlan(
        operations=[
            CreateIssueOperation(issue=issue, parent_epic=backlog.epics[0]),
            AddIssueToProjectOperation(issue=issue),
            UpdateIssueStatusOperation(issue=issue, current_status=None, desired_status="Ready"),
            CreateCommentOperation(item=issue, comment=issue.comments[0]),
        ]
    )

    bounded = workflow._bounded_reconciliation_plan(plan, max_operations=2)

    assert bounded.operations == plan.operations


def test_unbounded_reconcile_selects_the_complete_plan():
    backlog = _backlog()
    issue = backlog.epics[0].issues[0]
    plan = ExecutionPlan(
        operations=[
            CreateIssueOperation(issue=issue, parent_epic=backlog.epics[0]),
            AddIssueToProjectOperation(issue=issue),
            UpdateIssueStatusOperation(issue=issue, current_status=None, desired_status="Ready"),
            CreateCommentOperation(item=issue, comment=issue.comments[0]),
        ]
    )

    unbounded = workflow._bounded_reconciliation_plan(plan, max_operations=None)

    assert unbounded.operations == plan.operations


def test_reconcile_persists_each_completed_item_group(monkeypatch):
    events = []
    backlog = _backlog()
    issue = backlog.epics[0].issues[0]
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(
        workflow,
        "plan_reconcile_backlog",
        lambda **kwargs: ExecutionPlan(
            operations=[
                UpdateIssueStatusOperation(
                    issue=issue,
                    current_status="Backlog",
                    desired_status="Ready",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        workflow,
        "execute_reconciliation_plan",
        lambda **kwargs: events.append("github:execute-group"),
    )

    result = workflow.reconcile_backlog_from_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        max_operations=10,
        database_url="postgresql://example.test/db",
    )

    assert result.executed_group_count == 1
    assert events == [
        "github:execute-group",
        "transaction:begin",
        "database:save:test-epic:test-issue",
        "transaction:commit",
    ]


def test_reconcile_compensates_partial_created_issue_when_group_fails(monkeypatch):
    events = []
    backlog = _backlog()
    issue = backlog.epics[0].issues[0]
    issue.provider_metadata = {}
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(
        workflow,
        "plan_reconcile_backlog",
        lambda **kwargs: ExecutionPlan(
            operations=[
                CreateIssueOperation(issue=issue, parent_epic=backlog.epics[0]),
                AddIssueToProjectOperation(issue=issue),
            ]
        ),
    )

    def fail_after_create(**kwargs):
        issue.provider_metadata["github"] = {"issue_id": "I_partial"}
        raise RuntimeError("add to project failed")

    monkeypatch.setattr(workflow, "execute_reconciliation_plan", fail_after_create)
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:compensate-delete:{issue_id}"),
    )

    with pytest.raises(RuntimeError, match="add to project failed"):
        workflow.reconcile_backlog_from_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            max_operations=10,
            database_url="postgresql://example.test/db",
        )

    assert events == ["github:compensate-delete:I_partial"]


def test_purge_deletes_only_one_bounded_chunk_and_preserves_metadata(monkeypatch):
    events = []
    backlog = _backlog()
    transaction = FakeTransaction(backlog, events, clear_count=2)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(
        workflow,
        "list_project_issues",
        lambda project_id: [
            _live("epic", "I_epic2", 30, "epic"),
            _live("issue-a", "I_a", 31),
            _live("issue-b", "I_b", 32),
        ],
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    result = workflow.purge_backlog_projection_from_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        max_issues=2,
        database_url="postgresql://example.test/db",
    )

    assert result.total_issue_count == 3
    assert result.deleted_issue_count == 2
    assert result.remaining_issue_count == 1
    assert result.projection_metadata_cleared is False
    assert not any(event.startswith("database:clear") for event in events)
    assert events == ["github:delete:I_b", "github:delete:I_a"]


def test_purge_all_clears_item_and_comment_projection_metadata(monkeypatch):
    events = []
    backlog = _backlog()
    transaction = FakeTransaction(backlog, events, clear_count=2)
    _install_repository(monkeypatch, backlog, transaction)
    monkeypatch.setattr(
        workflow,
        "list_project_issues",
        lambda project_id: [_live("test-issue", "I_issue", 22)],
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    result = workflow.purge_backlog_projection_from_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        max_issues=None,
        database_url="postgresql://example.test/db",
    )

    assert result.remaining_issue_count == 0
    assert result.projection_metadata_cleared is True
    assert result.cleared_item_count == 2
    assert events == [
        "github:delete:I_issue",
        "transaction:begin",
        "database:clear-provider:github",
        "transaction:commit",
    ]
