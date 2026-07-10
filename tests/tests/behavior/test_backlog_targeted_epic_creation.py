import pytest

import johnny_johnny_agent.capabilities.backlog_persistence.workflow as workflow
from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogPersistenceError,
)
from johnny_johnny_agent.domain.backlog import Backlog, Epic, Project


class FakeTransaction:
    def __init__(self, backlog, events, *, update_error=None):
        self.backlog = backlog
        self.events = events
        self.update_error = update_error
        self.exit_exception_type = None

    def __enter__(self):
        self.events.append("transaction:begin")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exit_exception_type = exc_type
        self.events.append("transaction:commit" if exc_type is None else "transaction:rollback")
        return False

    def load_backlog(self, location, *, lock_project=False):
        self.events.append(f"database:load:lock={lock_project}")
        return self.backlog

    def insert_epic(self, location, epic):
        self.events.append(f"database:insert:{epic.id}")
        return "epic-row"

    def update_epic_provider_metadata(self, location, epic):
        self.events.append(f"database:update-metadata:{epic.id}")
        if self.update_error is not None:
            raise self.update_error


class FakeRepository:
    def __init__(self, transaction):
        self._transaction = transaction

    def transaction(self):
        return self._transaction


def test_create_epic_commits_database_after_targeted_github_projection(monkeypatch):
    events = []
    transaction = FakeTransaction(_empty_backlog(), events)
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(
        workflow,
        "get_repository",
        lambda owner, name: events.append(f"github:repository:{owner}/{name}")
        or {"id": "R_test"},
    )
    monkeypatch.setattr(
        workflow,
        "create_github_issue",
        lambda **kwargs: events.append("github:create-issue")
        or {
            "id": "I_test",
            "databaseId": 55,
            "number": 21,
            "url": "https://github.test/issues/21",
        },
    )
    monkeypatch.setattr(
        workflow,
        "add_issue_to_project",
        lambda project_id, issue_id: events.append("github:add-to-project")
        or {"id": "PVTI_test"},
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append("github:update-status") or {"id": "PVTI_test"},
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: pytest.fail("successful creation must not compensate"),
    )

    epic = workflow.create_epic_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        title="New Epic",
        repository_name="ggortsema/test-repo",
        epic_id="new-epic",
        description="Created transactionally.",
        acceptance_criteria=["Both sides agree."],
        database_url="postgresql://example.test/db",
    )

    assert events == [
        "transaction:begin",
        "database:load:lock=True",
        "database:insert:new-epic",
        "github:repository:ggortsema/test-repo",
        "github:create-issue",
        "github:add-to-project",
        "github:update-status",
        "database:update-metadata:new-epic",
        "transaction:commit",
    ]
    assert epic.provider_metadata == {
        "github": {
            "issue_id": "I_test",
            "database_id": 55,
            "number": 21,
            "url": "https://github.test/issues/21",
            "project_item_id": "PVTI_test",
            "project_id": "PVT_test",
        }
    }
    assert transaction.exit_exception_type is None


def test_github_failure_rolls_back_database_and_deletes_partial_issue(monkeypatch):
    events = []
    transaction = FakeTransaction(_empty_backlog(), events)
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(workflow, "get_repository", lambda owner, name: {"id": "R_test"})
    monkeypatch.setattr(
        workflow,
        "create_github_issue",
        lambda **kwargs: events.append("github:create-issue")
        or {"id": "I_partial", "number": 22, "url": "https://github.test/issues/22"},
    )

    def fail_add(project_id, issue_id):
        events.append("github:add-failed")
        raise RuntimeError("GitHub add-to-project failed")

    monkeypatch.setattr(workflow, "add_issue_to_project", fail_add)
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    with pytest.raises(RuntimeError, match="add-to-project failed"):
        workflow.create_epic_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            title="New Epic",
            repository_name="ggortsema/test-repo",
            epic_id="new-epic",
            database_url="postgresql://example.test/db",
        )

    assert "database:update-metadata:new-epic" not in events
    assert events[-2:] == ["github:delete:I_partial", "transaction:rollback"]
    assert transaction.exit_exception_type is RuntimeError


def test_database_finalization_failure_compensates_github_after_rollback(monkeypatch):
    events = []
    transaction = FakeTransaction(
        _empty_backlog(),
        events,
        update_error=ValueError("metadata update failed"),
    )
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(workflow, "get_repository", lambda owner, name: {"id": "R_test"})
    monkeypatch.setattr(
        workflow,
        "create_github_issue",
        lambda **kwargs: {"id": "I_test", "number": 23, "url": "https://github.test/issues/23"},
    )
    monkeypatch.setattr(
        workflow,
        "add_issue_to_project",
        lambda project_id, issue_id: {"id": "PVTI_test"},
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: {"id": "PVTI_test"},
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_issue",
        lambda issue_id: events.append(f"github:delete:{issue_id}"),
    )

    with pytest.raises(BacklogPersistenceError, match="metadata update failed"):
        workflow.create_epic_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            title="New Epic",
            repository_name="ggortsema/test-repo",
            epic_id="new-epic",
            database_url="postgresql://example.test/db",
        )

    assert events[-2:] == ["transaction:rollback", "github:delete:I_test"]
    assert transaction.exit_exception_type is ValueError


def test_retry_reuses_existing_github_epic_by_canonical_id(monkeypatch):
    events = []
    transaction = FakeTransaction(_empty_backlog(), events)
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(
        workflow,
        "list_project_issues",
        lambda project_id: [
            {
                "id": "I_existing",
                "database_id": 66,
                "number": 24,
                "url": "https://github.test/issues/24",
                "project_item_id": "PVTI_existing",
                "body": "<!-- johnny-johnny\nid: retry-epic\nschema: backlog-v1\ntype: epic\n-->",
            }
        ],
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append("github:update-existing-status")
        or {"id": "PVTI_existing"},
    )

    def fail_if_called(*args, **kwargs):
        pytest.fail("retry must reuse the existing Johnny-Johnny epic")

    monkeypatch.setattr(workflow, "get_repository", fail_if_called)
    monkeypatch.setattr(workflow, "create_github_issue", fail_if_called)
    monkeypatch.setattr(workflow, "add_issue_to_project", fail_if_called)
    monkeypatch.setattr(workflow, "delete_github_issue", fail_if_called)

    epic = workflow.create_epic_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        title="Retry Epic",
        repository_name="ggortsema/test-repo",
        epic_id="retry-epic",
        database_url="postgresql://example.test/db",
    )

    assert "github:update-existing-status" in events
    assert epic.provider_metadata["github"] == {
        "issue_id": "I_existing",
        "database_id": 66,
        "number": 24,
        "url": "https://github.test/issues/24",
        "project_item_id": "PVTI_existing",
        "project_id": "PVT_test",
    }
    assert events[-1] == "transaction:commit"



def test_existing_canonical_epic_repairs_missing_project_membership(monkeypatch):
    events = []
    backlog = _backlog_with_existing_epic()
    transaction = FakeTransaction(backlog, events)
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(
        workflow,
        "add_issue_to_project",
        lambda project_id, issue_id: events.append(
            f"github:add-existing:{project_id}:{issue_id}"
        ) or {"id": "PVTI_repaired"},
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: events.append("github:update-repaired-status")
        or {"id": "PVTI_repaired"},
    )

    def fail_if_called(*args, **kwargs):
        pytest.fail("repair must reuse the issue already stored in PostgreSQL")

    monkeypatch.setattr(workflow, "get_repository", fail_if_called)
    monkeypatch.setattr(workflow, "create_github_issue", fail_if_called)
    monkeypatch.setattr(workflow, "delete_github_issue", fail_if_called)
    monkeypatch.setattr(workflow, "delete_github_project_item", fail_if_called)

    epic = workflow.create_epic_in_postgres(
        provider="github",
        provider_account_username="ggortsema",
        provider_project_title="Test Project",
        title="Existing Epic",
        repository_name="ggortsema/test-repo",
        epic_id="existing-epic",
        description="Already canonical.",
        acceptance_criteria=["Projection is repaired."],
        database_url="postgresql://example.test/db",
    )

    assert "database:insert:existing-epic" not in events
    assert "github:add-existing:PVT_test:I_existing" in events
    assert epic.provider_metadata["github"] == {
        "issue_id": "I_existing",
        "database_id": 77,
        "number": 1887,
        "url": "https://github.test/issues/1887",
        "project_item_id": "PVTI_repaired",
        "project_id": "PVT_test",
    }
    assert events[-1] == "transaction:commit"


def test_existing_canonical_epic_rejects_conflicting_create_request(monkeypatch):
    events = []
    transaction = FakeTransaction(_backlog_with_existing_epic(), events)
    _install_repository(monkeypatch, transaction)
    monkeypatch.setattr(
        workflow,
        "list_project_issues",
        lambda project_id: pytest.fail("conflict must fail before GitHub"),
    )

    with pytest.raises(RuntimeError, match="different title"):
        workflow.create_epic_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            title="Different Title",
            repository_name="ggortsema/test-repo",
            epic_id="existing-epic",
            description="Already canonical.",
            acceptance_criteria=["Projection is repaired."],
            database_url="postgresql://example.test/db",
        )

    assert events[-1] == "transaction:rollback"


def test_repair_metadata_failure_removes_new_project_membership(monkeypatch):
    events = []
    transaction = FakeTransaction(
        _backlog_with_existing_epic(),
        events,
        update_error=ValueError("metadata update failed"),
    )
    _install_repository(monkeypatch, transaction)

    monkeypatch.setattr(workflow, "list_project_issues", lambda project_id: [])
    monkeypatch.setattr(
        workflow,
        "add_issue_to_project",
        lambda project_id, issue_id: {"id": "PVTI_repaired"},
    )
    monkeypatch.setattr(
        workflow,
        "update_project_item_status",
        lambda **kwargs: {"id": "PVTI_repaired"},
    )
    monkeypatch.setattr(
        workflow,
        "delete_github_project_item",
        lambda project_id, project_item_id: events.append(
            f"github:delete-project-item:{project_id}:{project_item_id}"
        ),
    )

    with pytest.raises(BacklogPersistenceError, match="metadata update failed"):
        workflow.create_epic_in_postgres(
            provider="github",
            provider_account_username="ggortsema",
            provider_project_title="Test Project",
            title="Existing Epic",
            repository_name="ggortsema/test-repo",
            epic_id="existing-epic",
            description="Already canonical.",
            acceptance_criteria=["Projection is repaired."],
            database_url="postgresql://example.test/db",
        )

    assert events[-2:] == [
        "transaction:rollback",
        "github:delete-project-item:PVT_test:PVTI_repaired",
    ]


def _backlog_with_existing_epic():
    backlog = _empty_backlog()
    backlog.epics.append(
        Epic(
            id="existing-epic",
            type="epic",
            title="Existing Epic",
            repository="ggortsema/test-repo",
            status="Backlog",
            issue_state="OPEN",
            order=1000,
            description="Already canonical.",
            acceptance_criteria=["Projection is repaired."],
            provider_metadata={
                "github": {
                    "issue_id": "I_existing",
                    "database_id": 77,
                    "number": 1887,
                    "url": "https://github.test/issues/1887",
                    "project_item_id": "PVTI_wrong_project",
                }
            },
        )
    )
    return backlog

def _install_repository(monkeypatch, transaction):
    monkeypatch.setattr(
        workflow,
        "PostgresBacklogRepository",
        lambda database_url: FakeRepository(transaction),
    )


def _empty_backlog():
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            number=1,
            url="https://github.test/projects/1",
            provider_metadata={"github": {"project_id": "PVT_test"}},
        ),
        epics=[],
    )
