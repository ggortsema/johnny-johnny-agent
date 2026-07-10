from typer.testing import CliRunner

from johnny_johnny_agent.cli.main import app

runner = CliRunner()


def test_backlog_help_exposes_canonical_command_groups():
    result = runner.invoke(app, ["backlog", "--help"])

    assert result.exit_code == 0
    assert "create" in result.output
    assert "list" in result.output
    assert "describe" in result.output
    assert "update" in result.output


def test_backlog_create_help_exposes_epic_and_issue_nouns():
    result = runner.invoke(app, ["backlog", "create", "--help"])

    assert result.exit_code == 0
    assert "epic" in result.output
    assert "issue" in result.output


def test_backlog_list_help_exposes_epics_and_items_collections():
    result = runner.invoke(app, ["backlog", "list", "--help"])

    assert result.exit_code == 0
    assert "epics" in result.output
    assert "items" in result.output


def test_list_epics_help_uses_database_project_identity_not_yaml_file():
    result = runner.invoke(app, ["backlog", "list", "epics", "--help"])

    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--provider" in result.output
    assert "--provider-account" in result.output
    assert "--database-url" in result.output
    assert "--file" not in result.output


def test_list_items_help_uses_database_project_identity_not_yaml_file():
    result = runner.invoke(app, ["backlog", "list", "items", "--help"])

    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--provider" in result.output
    assert "--provider-account" in result.output
    assert "--database-url" in result.output
    assert "--epic" in result.output
    assert "--status" in result.output
    assert "--exclude-status" in result.output
    assert "--file" not in result.output


def test_describe_help_uses_database_project_identity_not_yaml_file():
    result = runner.invoke(app, ["backlog", "describe", "--help"])

    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--provider" in result.output
    assert "--provider-account" in result.output
    assert "--database-url" in result.output
    assert "--file" not in result.output


def test_inspect_help_uses_database_project_identity_not_yaml_file():
    result = runner.invoke(app, ["backlog", "inspect", "--help"])

    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--provider" in result.output
    assert "--provider-account" in result.output
    assert "--database-url" in result.output
    assert "--file" not in result.output


def test_preview_epic_body_command_is_removed():
    result = runner.invoke(app, ["backlog", "preview-epic-body", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_create_issue_help_is_available():
    result = runner.invoke(app, ["backlog", "create", "issue", "--help"])

    assert result.exit_code == 0
    assert "--epic" in result.output
    assert "--title" in result.output
    assert "--dry-run" in result.output
    assert "--confirm" in result.output


def test_create_epic_help_is_available():
    result = runner.invoke(app, ["backlog", "create", "epic", "--help"])

    assert result.exit_code == 0
    assert "--title" in result.output
    assert "--repository" in result.output
    assert "--dry-run" in result.output
    assert "--confirm" in result.output


def test_update_help_uses_generic_backlog_item_language():
    result = runner.invoke(app, ["backlog", "update", "--help"])

    assert result.exit_code == 0
    assert "backlog item" in result.output.lower()
    assert "--status" in result.output
    assert "--comment" in result.output
    assert "--acceptance" in result.output

def test_move_help_is_available():
    result = runner.invoke(app, ["backlog", "move", "--help"])

    assert result.exit_code == 0
    assert "issue" in result.output.lower()
    assert "--to-epic" in result.output
    assert "--dry-run" in result.output
    assert "--confirm" in result.output

def test_legacy_create_issue_command_is_removed():
    result = runner.invoke(app, ["backlog", "create-issue", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_legacy_create_epic_command_is_removed():
    result = runner.invoke(app, ["backlog", "create-epic", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_legacy_update_issue_command_is_removed():
    result = runner.invoke(app, ["backlog", "update-issue", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_legacy_list_issues_command_is_removed():
    result = runner.invoke(app, ["backlog", "list-issues"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_legacy_list_epics_command_is_removed():
    result = runner.invoke(app, ["backlog", "list-epics"])

    assert result.exit_code != 0
    assert "No such command" in result.output