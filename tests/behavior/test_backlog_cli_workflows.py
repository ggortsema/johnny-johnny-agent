from types import SimpleNamespace

import yaml
from typer.testing import CliRunner

import johnny_johnny_agent.cli.main as cli_main
from johnny_johnny_agent.cli.main import app


runner = CliRunner()


def test_create_epic_workflow_saves_canonical_backlog(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    _disable_provider_reconciliation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "backlog",
            "create",
            "epic",
            "--file",
            str(backlog_file),
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
    assert "Created canonical epic: New Test Epic" in result.output
    assert "Saved:" in result.output

    backlog = _read_yaml(backlog_file)

    created_epic = _find_epic(backlog, "new-test-epic")

    assert created_epic["title"] == "New Test Epic"
    assert created_epic["repository"] == "ggortsema/test-repo"
    assert created_epic["status"] == "Backlog"
    assert created_epic["description"] == "A new epic created through the CLI."
    assert created_epic["acceptance_criteria"] == [
        "The epic exists in the canonical backlog."
    ]


def test_create_issue_workflow_saves_issue_under_parent_epic(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    _disable_provider_reconciliation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "backlog",
            "create",
            "issue",
            "--file",
            str(backlog_file),
            "--epic",
            "source-epic",
            "--id",
            "new-test-issue",
            "--title",
            "New Test Issue",
            "--description",
            "A new issue created through the CLI.",
            "--acceptance",
            "The issue exists under the source epic.",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Created canonical issue: New Test Issue" in result.output
    assert "Epic: source-epic" in result.output
    assert "Saved:" in result.output

    backlog = _read_yaml(backlog_file)
    source_epic = _find_epic(backlog, "source-epic")
    created_issue = _find_issue(source_epic, "new-test-issue")

    assert created_issue["title"] == "New Test Issue"
    assert created_issue["repository"] == source_epic["repository"]
    assert created_issue["status"] == "Backlog"
    assert created_issue["description"] == "A new issue created through the CLI."
    assert created_issue["acceptance_criteria"] == [
        "The issue exists under the source epic."
    ]


def test_update_issue_workflow_saves_canonical_changes(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    _disable_provider_reconciliation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "backlog",
            "update",
            "existing-issue",
            "--file",
            str(backlog_file),
            "--title",
            "Updated Issue Title",
            "--description",
            "Updated issue description.",
            "--status",
            "in progress",
            "--acceptance",
            "Updated acceptance criterion.",
            "--comment",
            "This was updated through the CLI.",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Updated canonical issue: Updated Issue Title" in result.output
    assert "Status: In Progress" in result.output
    assert "Saved:" in result.output

    backlog = _read_yaml(backlog_file)
    source_epic = _find_epic(backlog, "source-epic")
    issue = _find_issue(source_epic, "existing-issue")

    assert issue["title"] == "Updated Issue Title"
    assert issue["description"] == "Updated issue description."
    assert issue["status"] == "In Progress"
    assert issue["acceptance_criteria"] == ["Updated acceptance criterion."]
    assert len(issue["comments"]) == 1
    assert issue["comments"][0]["body"] == "This was updated through the CLI."


def test_move_issue_workflow_moves_issue_between_epics(tmp_path, monkeypatch):
    backlog_file = tmp_path / "backlog.yml"
    backlog_file.write_text(_minimal_backlog_yaml(), encoding="utf-8")

    _disable_provider_reconciliation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "backlog",
            "move",
            "existing-issue",
            "--file",
            str(backlog_file),
            "--to-epic",
            "target-epic",
            "--confirm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Moved canonical issue: Existing Issue" in result.output
    assert "Epic: target-epic" in result.output
    assert "Repository: ggortsema/target-repo" in result.output
    assert "Saved:" in result.output

    backlog = _read_yaml(backlog_file)
    source_epic = _find_epic(backlog, "source-epic")
    target_epic = _find_epic(backlog, "target-epic")

    assert _find_issue_or_none(source_epic, "existing-issue") is None

    moved_issue = _find_issue(target_epic, "existing-issue")

    assert moved_issue["title"] == "Existing Issue"
    assert moved_issue["repository"] == "ggortsema/target-repo"
    assert moved_issue["milestone"] == "Target Milestone"
    assert moved_issue["order"] == 1000


def _disable_provider_reconciliation(monkeypatch):
    monkeypatch.setattr(
        cli_main,
        "_plan_reconcile",
        lambda backlog: SimpleNamespace(operations=[]),
    )

    monkeypatch.setattr(
        cli_main,
        "execute_reconciliation_plan",
        lambda *args, **kwargs: None,
    )


def _read_yaml(backlog_file):
    return yaml.safe_load(backlog_file.read_text(encoding="utf-8"))


def _find_epic(backlog, epic_id):
    for epic in backlog["epics"]:
        if epic["id"] == epic_id:
            return epic

    raise AssertionError(f"Epic not found: {epic_id}")


def _find_issue(epic, issue_id):
    issue = _find_issue_or_none(epic, issue_id)

    if issue is None:
        raise AssertionError(f"Issue not found: {issue_id}")

    return issue


def _find_issue_or_none(epic, issue_id):
    for issue in epic["issues"]:
        if issue["id"] == issue_id:
            return issue

    return None


def _minimal_backlog_yaml():
    return """\
version: 1
project:
  provider: github
  title: Test Project
  number: 1
  url: https://github.com/users/ggortsema/projects/1
  provider_metadata:
    github:
      project_id: test-project-id
epics:
- id: source-epic
  type: epic
  title: Source Epic
  repository: ggortsema/source-repo
  status: Backlog
  issue_state: OPEN
  order: 1000
  description: Source epic description.
  acceptance_criteria: []
  comments: []
  labels: []
  assignees: []
  milestone: Source Milestone
  provider_metadata:
    github: {}
  issues:
  - id: existing-issue
    type: issue
    title: Existing Issue
    repository: ggortsema/source-repo
    status: Ready
    issue_state: OPEN
    order: 1000
    description: Existing issue description.
    acceptance_criteria:
    - Existing acceptance criterion.
    comments: []
    labels: []
    assignees: []
    milestone: Source Milestone
    provider_metadata:
      github: {}
- id: target-epic
  type: epic
  title: Target Epic
  repository: ggortsema/target-repo
  status: Backlog
  issue_state: OPEN
  order: 2000
  description: Target epic description.
  acceptance_criteria: []
  comments: []
  labels: []
  assignees: []
  milestone: Target Milestone
  provider_metadata:
    github: {}
  issues: []
"""