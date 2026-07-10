from typer.testing import CliRunner

import johnny_johnny_agent.cli.main as cli_main
from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogImportResult,
    BacklogLocation,
    DatabaseStatus,
)
from johnny_johnny_agent.capabilities.backlog_persistence.workflow import (
    BacklogExportResult,
)
from johnny_johnny_agent.cli.main import app
from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue, Project


runner = CliRunner()


def test_database_check_reports_canonical_schema_readiness(monkeypatch):
    monkeypatch.setattr(
        cli_main,
        "check_postgres_backlog_database",
        lambda database_url=None: DatabaseStatus(
            database="styxcd",
            database_user="rincexwind",
            schema="johnny_johnny",
            server_version="15.8",
            available_tables=(
                "backlog_item_acceptance_criteria",
                "backlog_item_assignees",
                "backlog_item_comments",
                "backlog_item_labels",
                "backlog_items",
                "provider_accounts",
                "provider_projects",
                "providers",
                "users",
            ),
            missing_tables=(),
            provider_count=5,
        ),
    )

    result = runner.invoke(app, ["backlog", "db", "check"])

    assert result.exit_code == 0, result.output
    assert "PostgreSQL connection: OK" in result.output
    assert "Database: styxcd" in result.output
    assert "Schema: johnny_johnny" in result.output
    assert "Canonical tables: 9/9" in result.output
    assert "Seeded providers: 5" in result.output
    assert "Canonical backlog persistence: ready" in result.output


def test_database_import_dry_run_does_not_connect(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    def fail_if_called(**kwargs):
        raise AssertionError("database import should not run during --dry-run")

    monkeypatch.setattr(cli_main, "import_backlog_yaml_to_postgres", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog",
            "db",
            "import",
            "--file",
            str(backlog_file),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Mode: transactional snapshot replacement" in result.output
    assert "Epics: 1" in result.output
    assert "Issues: 1" in result.output
    assert "Comments: 1" in result.output
    assert "No database changes made." in result.output


def test_database_import_confirm_executes_verified_replacement(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    captured = {}

    def fake_import(**kwargs):
        captured.update(kwargs)
        return BacklogImportResult(
            location=BacklogLocation(
                provider="github",
                provider_account_username="ggortsema",
                project_title="Test Project",
            ),
            provider_project_id="project-1",
            epic_count=1,
            issue_count=1,
            acceptance_criterion_count=2,
            comment_count=1,
            label_count=1,
            assignee_count=1,
            verified=True,
        )

    monkeypatch.setattr(cli_main, "import_backlog_yaml_to_postgres", fake_import)

    result = runner.invoke(
        app,
        [
            "backlog",
            "db",
            "import",
            "--file",
            str(backlog_file),
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["backlog_path"] == str(backlog_file)
    assert captured["verify"] is True
    assert "Imported canonical backlog into PostgreSQL." in result.output
    assert "Project: github / ggortsema / Test Project" in result.output
    assert "Round-trip verified: yes" in result.output


def test_list_epics_reads_selected_project_directly_from_postgres(monkeypatch):
    captured = {}

    backlog = Backlog(
        project=Project(
            provider="github",
            title="Test Project",
        ),
        epics=[
            Epic(
                id="second-epic",
                type="epic",
                title="Second Epic",
                repository="ggortsema/test-repo",
                status="Ready",
                issue_state="OPEN",
                order=2000,
            ),
            Epic(
                id="first-epic",
                type="epic",
                title="First Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
            ),
        ],
    )

    def fake_load(**kwargs):
        captured.update(kwargs)
        return backlog

    def fail_if_yaml_is_loaded(*args, **kwargs):
        raise AssertionError("list epics must not load YAML")

    monkeypatch.setattr(cli_main, "load_backlog_from_postgres", fake_load)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_yaml_is_loaded)

    result = runner.invoke(
        app,
        [
            "backlog",
            "list",
            "epics",
            "--project",
            "Test Project",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "database_url": None,
    }
    assert result.output.index("first-epic") < result.output.index("second-epic")
    assert "First Epic" in result.output
    assert "Second Epic" in result.output


def test_list_items_reads_selected_project_directly_from_postgres(monkeypatch):
    captured = {}

    first_issue = Issue(
        id="first-issue",
        type="issue",
        title="First Issue",
        repository="ggortsema/test-repo",
        status="Ready",
        issue_state="OPEN",
        order=1000,
    )
    second_issue = Issue(
        id="second-issue",
        type="issue",
        title="Second Issue",
        repository="ggortsema/test-repo",
        status="Ready",
        issue_state="OPEN",
        order=2000,
    )
    backlog = Backlog(
        project=Project(
            provider="github",
            title="Test Project",
        ),
        epics=[
            Epic(
                id="first-epic",
                type="epic",
                title="First Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
                issues=[second_issue, first_issue],
            ),
        ],
    )

    def fake_load(**kwargs):
        captured.update(kwargs)
        return backlog

    def fail_if_yaml_is_loaded(*args, **kwargs):
        raise AssertionError("list items must not load YAML")

    monkeypatch.setattr(cli_main, "load_backlog_from_postgres", fake_load)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_yaml_is_loaded)

    result = runner.invoke(
        app,
        [
            "backlog",
            "list",
            "items",
            "--project",
            "Test Project",
            "--epic",
            "first-epic",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "database_url": None,
    }
    assert result.output.index("first-issue") < result.output.index("second-issue")
    assert "First Issue" in result.output
    assert "Second Issue" in result.output


def test_list_items_preserves_status_filters_for_postgres_backlog(monkeypatch):
    backlog = Backlog(
        project=Project(
            provider="github",
            title="Test Project",
        ),
        epics=[
            Epic(
                id="first-epic",
                type="epic",
                title="First Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
                issues=[
                    Issue(
                        id="ready-issue",
                        type="issue",
                        title="Ready Issue",
                        repository="ggortsema/test-repo",
                        status="Ready",
                        issue_state="OPEN",
                        order=1000,
                    ),
                    Issue(
                        id="done-issue",
                        type="issue",
                        title="Done Issue",
                        repository="ggortsema/test-repo",
                        status="Done",
                        issue_state="CLOSED",
                        order=2000,
                    ),
                ],
            ),
        ],
    )

    monkeypatch.setattr(
        cli_main,
        "load_backlog_from_postgres",
        lambda **kwargs: backlog,
    )

    result = runner.invoke(
        app,
        [
            "backlog",
            "list",
            "items",
            "--project",
            "Test Project",
            "--status",
            "ready",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "ready-issue" in result.output
    assert "done-issue" not in result.output


def test_inspect_reads_selected_project_directly_from_postgres(monkeypatch):
    captured = {}

    backlog = Backlog(
        project=Project(
            provider="github",
            title="Test Project",
        ),
        epics=[
            Epic(
                id="test-epic",
                type="epic",
                title="Test Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
                issues=[
                    Issue(
                        id="first-issue",
                        type="issue",
                        title="First Issue",
                        repository="ggortsema/test-repo",
                        status="Ready",
                        issue_state="OPEN",
                        order=1000,
                    ),
                    Issue(
                        id="second-issue",
                        type="issue",
                        title="Second Issue",
                        repository="ggortsema/test-repo",
                        status="Done",
                        issue_state="CLOSED",
                        order=2000,
                    ),
                ],
            ),
        ],
    )

    def fake_load(**kwargs):
        captured.update(kwargs)
        return backlog

    def fail_if_yaml_is_loaded(*args, **kwargs):
        raise AssertionError("inspect must not load YAML")

    monkeypatch.setattr(cli_main, "load_backlog_from_postgres", fake_load)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_yaml_is_loaded)

    result = runner.invoke(
        app,
        [
            "backlog",
            "inspect",
            "--project",
            "Test Project",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "database_url": None,
    }
    assert "Project: Test Project" in result.output
    assert "Provider: github" in result.output
    assert "Epics: 1" in result.output
    assert "Issues: 2" in result.output


def test_describe_reads_selected_item_directly_from_postgres(monkeypatch):
    captured = {}

    backlog = Backlog(
        project=Project(
            provider="github",
            title="Test Project",
        ),
        epics=[
            Epic(
                id="test-epic",
                type="epic",
                title="Test Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
                issues=[
                    Issue(
                        id="test-issue",
                        type="issue",
                        title="Test Issue",
                        repository="ggortsema/test-repo",
                        status="Ready",
                        issue_state="OPEN",
                        order=1000,
                        description="Loaded directly from PostgreSQL.",
                    ),
                ],
            ),
        ],
    )

    def fake_load(**kwargs):
        captured.update(kwargs)
        return backlog

    def fail_if_yaml_is_loaded(*args, **kwargs):
        raise AssertionError("describe must not load YAML")

    monkeypatch.setattr(cli_main, "load_backlog_from_postgres", fake_load)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_yaml_is_loaded)

    result = runner.invoke(
        app,
        [
            "backlog",
            "describe",
            "test-issue",
            "--project",
            "Test Project",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "database_url": None,
    }
    assert "Test Issue" in result.output
    assert "Loaded directly from PostgreSQL." in result.output
    assert "Test Epic [test-epic]" in result.output


def test_database_export_writes_selected_project(monkeypatch):
    captured = {}

    def fake_export(**kwargs):
        captured.update(kwargs)
        return BacklogExportResult(
            location=BacklogLocation(
                provider="github",
                provider_account_username="ggortsema",
                project_title="Test Project",
            ),
            output_path="data/output/backlog-from-db.yml",
            epic_count=1,
            issue_count=2,
            comment_count=3,
        )

    monkeypatch.setattr(cli_main, "export_backlog_yaml_from_postgres", fake_export)

    result = runner.invoke(
        app,
        [
            "backlog",
            "db",
            "export",
            "--project",
            "Test Project",
            "--output",
            "data/output/backlog-from-db.yml",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["provider_project_title"] == "Test Project"
    assert captured["provider_account_username"] == "ggortsema"
    assert "Exported canonical backlog from PostgreSQL." in result.output
    assert "Wrote: data/output/backlog-from-db.yml" in result.output


def _minimal_backlog_yaml():
    return """\
version: 1
project:
  provider: github
  title: Test Project
  number: 1
  url: https://example.test/projects/1
  provider_metadata:
    github:
      project_id: PVT_test
epics:
- id: test-epic
  type: epic
  title: Test Epic
  repository: ggortsema/test-repo
  status: In Progress
  issue_state: OPEN
  order: 1000
  description: Test epic.
  acceptance_criteria:
  - Epic criterion.
  comments: []
  labels: []
  assignees: []
  milestone: null
  provider_metadata:
    github: {}
  issues:
  - id: test-issue
    type: issue
    title: Test Issue
    repository: ggortsema/test-repo
    status: Ready
    issue_state: OPEN
    order: 1000
    description: Test issue.
    acceptance_criteria:
    - Issue criterion.
    comments:
    - id: comment-1
      body: Test comment.
      source: johnny-johnny
      created_at: '2026-07-10T12:00:00+00:00'
      provider_metadata:
        github: {}
    labels:
    - database
    assignees:
    - ggortsema
    milestone: null
    provider_metadata:
      github: {}
"""
