from datetime import datetime, timezone

import pytest

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogLocation,
    PostgresBacklogRepository,
    RoundTripValidationError,
)
from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue, Project


class FakeResult:
    def __init__(self, rows=None):
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class ImportConnection:
    def __init__(self):
        self.statements = []
        self.exit_exception_type = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exit_exception_type = exc_type
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))

        if "SELECT id FROM users" in normalized:
            return FakeResult()
        if "INSERT INTO users" in normalized:
            return FakeResult({"id": "user-1"})
        if "INSERT INTO providers" in normalized:
            return FakeResult({"id": "provider-1"})
        if "INSERT INTO provider_accounts" in normalized:
            return FakeResult({"id": "account-1"})
        if "INSERT INTO provider_projects" in normalized:
            return FakeResult({"id": "project-1"})
        if "INSERT INTO backlog_items" in normalized:
            return FakeResult({"id": f"row-{params[2]}"})

        return FakeResult()


class LoadConnection:
    def __init__(self):
        self.exit_exception_type = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exit_exception_type = exc_type
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())

        if normalized.startswith("SET search_path"):
            return FakeResult()

        if "FROM provider_projects pp" in normalized:
            return FakeResult(
                {
                    "id": "project-1",
                    "title": "Test Project",
                    "external_id": "PVT_test",
                    "external_number": 7,
                    "url": "https://example.test/project/7",
                    "provider_metadata": {},
                    "provider_key": "github",
                    "provider_account_username": "ggortsema",
                }
            )

        if "SELECT * FROM backlog_items" in normalized:
            return FakeResult(
                [
                    _item_row(
                        row_id="epic-row",
                        parent_id=None,
                        canonical_id="test-epic",
                        item_type="epic",
                        title="Test Epic",
                        order=1000,
                    ),
                    _item_row(
                        row_id="issue-row",
                        parent_id="epic-row",
                        canonical_id="test-issue",
                        item_type="issue",
                        title="Test Issue",
                        order=1000,
                        external_id="I_test",
                        external_database_id=42,
                        external_number=12,
                        external_url="https://example.test/issues/12",
                        external_project_item_id="PVTI_test",
                    ),
                ]
            )

        if "FROM backlog_item_acceptance_criteria ac" in normalized:
            return FakeResult(
                [
                    {"backlog_item_id": "epic-row", "body": "Epic criterion"},
                    {"backlog_item_id": "issue-row", "body": "Issue criterion"},
                ]
            )

        if "FROM backlog_item_comments c" in normalized:
            return FakeResult(
                [
                    {
                        "id": "comment-row",
                        "backlog_item_id": "issue-row",
                        "canonical_comment_id": "comment-1",
                        "body": "Persisted comment",
                        "source": "johnny-johnny",
                        "created_at": datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
                        "provider_metadata": {"github": {"comment_id": "IC_test"}},
                    }
                ]
            )

        if "FROM backlog_item_labels l" in normalized:
            return FakeResult(
                [
                    {"backlog_item_id": "issue-row", "label": "backend"},
                    {"backlog_item_id": "issue-row", "label": "database"},
                ]
            )

        if "FROM backlog_item_assignees a" in normalized:
            return FakeResult(
                [{"backlog_item_id": "issue-row", "assignee": "ggortsema"}]
            )

        raise AssertionError(f"Unexpected SQL: {normalized}")


class InsertEpicConnection:
    def __init__(self):
        self.statements = []
        self.exit_exception_type = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exit_exception_type = exc_type
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))

        if normalized.startswith("SET search_path"):
            return FakeResult()
        if "FROM provider_projects pp" in normalized:
            return FakeResult({
                "id": "project-1",
                "provider_key": "github",
                "provider_account_username": "ggortsema",
            })
        if "INSERT INTO backlog_items" in normalized:
            return FakeResult({"id": "epic-row"})
        if normalized.startswith("UPDATE backlog_items"):
            return FakeResult({"id": "epic-row"})

        return FakeResult()


def test_replace_imports_a_complete_snapshot_with_explicit_schema():
    connection = ImportConnection()
    repository = PostgresBacklogRepository(
        "postgresql://example.test/db",
        connection_factory=lambda database_url: connection,
    )

    result = repository.replace(
        _sample_backlog(),
        user_display_name="Grant Gortsema",
        user_primary_email=None,
        provider_account_username="ggortsema",
        provider_account_display_name="Grant Gortsema",
        verify=False,
    )

    assert result.epic_count == 1
    assert result.issue_count == 1
    assert result.acceptance_criterion_count == 2
    assert result.comment_count == 1
    assert result.verified is False
    assert connection.exit_exception_type is None

    statements = [statement for statement, _ in connection.statements]
    assert statements[0] == "SET search_path TO johnny_johnny, public"
    assert any(
        statement.startswith("DELETE FROM backlog_items WHERE provider_project_id")
        for statement in statements
    )
    assert sum("INSERT INTO backlog_items" in statement for statement in statements) == 2
    assert sum(
        "INSERT INTO backlog_item_acceptance_criteria" in statement
        for statement in statements
    ) == 2
    assert sum(
        "INSERT INTO backlog_item_comments" in statement
        for statement in statements
    ) == 1


def test_replace_rolls_back_when_round_trip_verification_differs():
    connection = ImportConnection()

    class MismatchRepository(PostgresBacklogRepository):
        def _load_backlog(self, conn, location):
            return Backlog(
                project=Project(
                    provider="github",
                    title="Test Project",
                    number=1,
                    url="https://example.test/project/1",
                    provider_metadata={"github": {"project_id": "PVT_test"}},
                ),
                epics=[],
            )

    repository = MismatchRepository(
        "postgresql://example.test/db",
        connection_factory=lambda database_url: connection,
    )

    with pytest.raises(RoundTripValidationError, match="verification failed"):
        repository.replace(
            _sample_backlog(),
            user_display_name="Grant Gortsema",
            user_primary_email=None,
            provider_account_username="ggortsema",
            provider_account_display_name="Grant Gortsema",
            verify=True,
        )

    assert connection.exit_exception_type is RoundTripValidationError


def test_load_reconstructs_the_provider_independent_domain_model():
    connection = LoadConnection()
    repository = PostgresBacklogRepository(
        "postgresql://example.test/db",
        connection_factory=lambda database_url: connection,
    )

    backlog = repository.load(
        BacklogLocation(
            provider="github",
            provider_account_username="ggortsema",
            project_title="Test Project",
        )
    )

    assert backlog.project.provider_metadata == {
        "github": {"project_id": "PVT_test"}
    }
    assert len(backlog.epics) == 1

    epic = backlog.epics[0]
    assert epic.id == "test-epic"
    assert epic.acceptance_criteria == ["Epic criterion"]
    assert len(epic.issues) == 1

    issue = epic.issues[0]
    assert issue.id == "test-issue"
    assert issue.acceptance_criteria == ["Issue criterion"]
    assert issue.labels == ["backend", "database"]
    assert issue.assignees == ["ggortsema"]
    assert issue.provider_metadata == {
        "github": {
            "issue_id": "I_test",
            "database_id": 42,
            "number": 12,
            "url": "https://example.test/issues/12",
            "project_item_id": "PVTI_test",
        }
    }
    assert issue.comments == [
        Comment(
            id="comment-1",
            body="Persisted comment",
            source="johnny-johnny",
            created_at="2026-07-10T12:00:00+00:00",
            provider_metadata={"github": {"comment_id": "IC_test"}},
        )
    ]
    assert connection.exit_exception_type is None


def test_insert_epic_writes_only_the_new_epic_and_its_children():
    connection = InsertEpicConnection()
    repository = PostgresBacklogRepository(
        "postgresql://example.test/db",
        connection_factory=lambda database_url: connection,
    )
    epic = Epic(
        id="new-epic",
        type="epic",
        title="New Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=3000,
        description="Created directly in PostgreSQL.",
        acceptance_criteria=["The epic is persisted."],
        provider_metadata={"github": {}},
    )

    result = repository.insert_epic(
        BacklogLocation(
            provider="github",
            provider_account_username="ggortsema",
            project_title="Test Project",
        ),
        epic,
    )

    assert result is epic
    statements = [statement for statement, _ in connection.statements]
    assert statements[0] == "SET search_path TO johnny_johnny, public"
    assert sum("INSERT INTO backlog_items" in statement for statement in statements) == 1
    assert sum(
        "INSERT INTO backlog_item_acceptance_criteria" in statement
        for statement in statements
    ) == 1
    assert not any(statement.startswith("DELETE FROM backlog_items") for statement in statements)
    assert connection.exit_exception_type is None


def test_transaction_updates_epic_provider_metadata_before_commit():
    connection = InsertEpicConnection()
    repository = PostgresBacklogRepository(
        "postgresql://example.test/db",
        connection_factory=lambda database_url: connection,
    )
    location = BacklogLocation(
        provider="github",
        provider_account_username="ggortsema",
        project_title="Test Project",
    )
    epic = Epic(
        id="new-epic",
        type="epic",
        title="New Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=3000,
        provider_metadata={"github": {}},
    )

    with repository.transaction() as transaction:
        transaction.insert_epic(location, epic)
        epic.provider_metadata["github"] = {
            "issue_id": "I_test",
            "database_id": 77,
            "number": 25,
            "url": "https://github.test/issues/25",
            "project_item_id": "PVTI_test",
        }
        transaction.update_epic_provider_metadata(location, epic)

    update_statements = [
        (statement, params)
        for statement, params in connection.statements
        if statement.startswith("UPDATE backlog_items")
    ]
    assert len(update_statements) == 1
    _, params = update_statements[0]
    assert params[8:13] == (
        "I_test",
        77,
        25,
        "https://github.test/issues/25",
        "PVTI_test",
    )
    assert params[-2:] == ("new-epic", "epic")
    assert connection.exit_exception_type is None


def _sample_backlog():
    issue = Issue(
        id="test-issue",
        type="issue",
        title="Test Issue",
        repository="ggortsema/test-repo",
        status="Ready",
        issue_state="OPEN",
        order=1000,
        description="Issue description",
        acceptance_criteria=["Issue criterion"],
        comments=[
            Comment(
                id="comment-1",
                body="Persisted comment",
                created_at="2026-07-10T12:00:00Z",
                provider_metadata={"github": {"comment_id": "IC_test"}},
            )
        ],
        labels=["database"],
        assignees=["ggortsema"],
        provider_metadata={
            "github": {
                "issue_id": "I_test",
                "database_id": 42,
                "number": 12,
                "url": "https://example.test/issues/12",
                "project_item_id": "PVTI_test",
            }
        },
    )
    epic = Epic(
        id="test-epic",
        type="epic",
        title="Test Epic",
        repository="ggortsema/test-repo",
        status="In Progress",
        issue_state="OPEN",
        order=1000,
        description="Epic description",
        acceptance_criteria=["Epic criterion"],
        provider_metadata={"github": {}},
        issues=[issue],
    )
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            number=1,
            url="https://example.test/project/1",
            provider_metadata={"github": {"project_id": "PVT_test"}},
        ),
        epics=[epic],
    )


def _item_row(
    *,
    row_id,
    parent_id,
    canonical_id,
    item_type,
    title,
    order,
    external_id=None,
    external_database_id=None,
    external_number=None,
    external_url=None,
    external_project_item_id=None,
):
    return {
        "id": row_id,
        "provider_project_id": "project-1",
        "parent_item_id": parent_id,
        "canonical_id": canonical_id,
        "item_type": item_type,
        "title": title,
        "description": f"{title} description",
        "repository": "ggortsema/test-repo",
        "status": "Ready",
        "issue_state": "OPEN",
        "item_order": order,
        "milestone": None,
        "external_id": external_id,
        "external_database_id": external_database_id,
        "external_number": external_number,
        "external_url": external_url,
        "external_project_item_id": external_project_item_id,
        "provider_metadata": {},
    }
