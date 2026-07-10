from typer.testing import CliRunner

import johnny_johnny_agent.cli.main as cli_main
from johnny_johnny_agent.cli.main import app
from johnny_johnny_agent.domain.backlog import Comment, Epic, Issue


runner = CliRunner()


def test_create_epic_workflow_commits_postgres_and_github_without_yaml(monkeypatch):
    captured = {}

    def fake_create_epic_in_postgres(**kwargs):
        captured.update(kwargs)
        return Epic(
            id="new-test-epic",
            type="epic",
            title="New Test Epic",
            repository="ggortsema/test-repo",
            status="Backlog",
            issue_state="OPEN",
            order=3000,
            description="A new epic created through the CLI.",
            acceptance_criteria=[
                "The epic exists in the canonical backlog."
            ],
            provider_metadata={
                "github": {
                    "issue_id": "I_new",
                    "database_id": 123,
                    "number": 44,
                    "url": "https://github.test/issues/44",
                    "project_item_id": "PVTI_new",
                }
            },
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("create epic must not use YAML or full-project reconcile")

    monkeypatch.setattr(
        cli_main,
        "create_epic_in_postgres",
        fake_create_epic_in_postgres,
    )
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "save_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "_plan_reconcile", fail_if_called)
    monkeypatch.setattr(cli_main, "execute_reconciliation_plan", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog",
            "create",
            "epic",
            "--project",
            "Test Project",
            "--id",
            "new-test-epic",
            "--title",
            "New Test Epic",
            "--repository",
            "ggortsema/test-repo",
            "--description",
            "A new epic created through the CLI.",
            "--acceptance",
            "The epic exists in the canonical backlog.",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "title": "New Test Epic",
        "repository_name": "ggortsema/test-repo",
        "epic_id": "new-test-epic",
        "description": "A new epic created through the CLI.",
        "acceptance_criteria": [
            "The epic exists in the canonical backlog."
        ],
        "database_url": None,
    }
    assert "Synchronized canonical epic: New Test Epic" in result.output
    assert "Project: github / ggortsema / Test Project" in result.output
    assert "GitHub issue: #44" in result.output
    assert "GitHub URL: https://github.test/issues/44" in result.output
    assert "Canonical and provider state committed." in result.output


def test_create_epic_dry_run_previews_without_writing(monkeypatch):
    captured = {}

    def fake_preview_create_epic_in_postgres(**kwargs):
        captured.update(kwargs)
        return Epic(
            id="preview-epic",
            type="epic",
            title="Preview Epic",
            repository="ggortsema/test-repo",
            status="Backlog",
            issue_state="OPEN",
            order=3000,
            provider_metadata={"github": {}},
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run must not insert the epic")

    monkeypatch.setattr(
        cli_main,
        "preview_create_epic_in_postgres",
        fake_preview_create_epic_in_postgres,
    )
    monkeypatch.setattr(cli_main, "create_epic_in_postgres", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog",
            "create",
            "epic",
            "--project",
            "Test Project",
            "--title",
            "Preview Epic",
            "--repository",
            "ggortsema/test-repo",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["provider_project_title"] == "Test Project"
    assert captured["title"] == "Preview Epic"
    assert "Canonical epic preview: Preview Epic" in result.output
    assert "No PostgreSQL or GitHub changes made." in result.output
    assert "Canonical and provider state committed." not in result.output

def test_create_issue_workflow_commits_postgres_and_github_without_yaml(monkeypatch):
    captured = {}
    parent = Epic(
        id="source-epic",
        type="epic",
        title="Source Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=1000,
    )

    def fake_create_issue_in_postgres(**kwargs):
        captured.update(kwargs)
        return (
            Issue(
                id="new-test-issue",
                type="issue",
                title="New Test Issue",
                repository="ggortsema/test-repo",
                status="Backlog",
                issue_state="OPEN",
                order=1000,
                description="A new issue created through the CLI.",
                acceptance_criteria=["The issue exists under the source epic."],
                provider_metadata={
                    "github": {
                        "number": 45,
                        "url": "https://github.test/issues/45",
                    }
                },
            ),
            parent,
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("database-backed create issue must not use YAML or full reconcile")

    monkeypatch.setattr(cli_main, "create_issue_in_postgres", fake_create_issue_in_postgres)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "save_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "execute_reconciliation_plan", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog", "create", "issue",
            "--project", "Test Project",
            "--epic", "source-epic",
            "--id", "new-test-issue",
            "--title", "New Test Issue",
            "--description", "A new issue created through the CLI.",
            "--acceptance", "The issue exists under the source epic.",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["provider_project_title"] == "Test Project"
    assert captured["parent_epic_id"] == "source-epic"
    assert "Synchronized canonical issue: New Test Issue" in result.output
    assert "GitHub issue: #45" in result.output
    assert "Canonical and provider state committed." in result.output


def test_update_issue_workflow_commits_postgres_and_github_without_yaml(monkeypatch):
    captured = {}

    def fake_update_item_in_postgres(**kwargs):
        captured.update(kwargs)
        return Issue(
            id="existing-issue",
            type="issue",
            title="Updated Issue Title",
            repository="ggortsema/test-repo",
            status="In Progress",
            issue_state="OPEN",
            order=1000,
            description="Updated issue description.",
            acceptance_criteria=["Updated acceptance criterion."],
            comments=[Comment(id="comment-1", body="This was updated through the CLI.")],
            provider_metadata={
                "github": {
                    "number": 46,
                    "url": "https://github.test/issues/46",
                }
            },
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("database-backed update must not use YAML or full reconcile")

    monkeypatch.setattr(cli_main, "update_item_in_postgres", fake_update_item_in_postgres)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "save_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "execute_reconciliation_plan", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog", "update", "existing-issue",
            "--project", "Test Project",
            "--title", "Updated Issue Title",
            "--description", "Updated issue description.",
            "--status", "in progress",
            "--acceptance", "Updated acceptance criterion.",
            "--comment", "This was updated through the CLI.",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["item_id"] == "existing-issue"
    assert captured["status"] == "in progress"
    assert "Synchronized canonical issue: Updated Issue Title" in result.output
    assert "Status: In Progress" in result.output
    assert "GitHub issue: #46" in result.output


def test_move_issue_workflow_commits_postgres_and_github_without_yaml(monkeypatch):
    captured = {}
    source = Epic(
        id="source-epic",
        type="epic",
        title="Source Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=1000,
    )
    target = Epic(
        id="target-epic",
        type="epic",
        title="Target Epic",
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=2000,
    )

    def fake_move_issue_in_postgres(**kwargs):
        captured.update(kwargs)
        return (
            Issue(
                id="existing-issue",
                type="issue",
                title="Existing Issue",
                repository="ggortsema/test-repo",
                status="Ready",
                issue_state="OPEN",
                order=1000,
                provider_metadata={
                    "github": {
                        "number": 47,
                        "url": "https://github.test/issues/47",
                    }
                },
            ),
            source,
            target,
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("database-backed move must not use YAML or full reconcile")

    monkeypatch.setattr(cli_main, "move_issue_in_postgres", fake_move_issue_in_postgres)
    monkeypatch.setattr(cli_main, "load_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "save_backlog_yaml", fail_if_called)
    monkeypatch.setattr(cli_main, "execute_reconciliation_plan", fail_if_called)

    result = runner.invoke(
        app,
        [
            "backlog", "move", "existing-issue",
            "--project", "Test Project",
            "--to-epic", "target-epic",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["issue_id"] == "existing-issue"
    assert captured["target_epic_id"] == "target-epic"
    assert "Synchronized canonical issue: Existing Issue" in result.output
    assert "From epic: source-epic" in result.output
    assert "To epic: target-epic" in result.output
    assert "GitHub issue: #47" in result.output

