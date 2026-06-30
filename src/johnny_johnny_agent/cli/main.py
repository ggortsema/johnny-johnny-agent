from typing import Annotated

import typer
import uvicorn
import json

from johnny_johnny_agent.capabilities.backlog_sync.workflow import (
    publish_backlog_from_markdown,
)
from johnny_johnny_agent.capabilities.github.project_reader import print_project_issues
from johnny_johnny_agent.capabilities.backlog_sync.validator import (
    validate_backlog_yaml,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_loader import load_backlog_yaml
from johnny_johnny_agent.capabilities.github.renderer import render_epic_body
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    UpdateIssueStatusOperation,
    plan_reconcile_backlog,
)
from johnny_johnny_agent.capabilities.backlog_sync.executor import (
    execute_reconciliation_plan,
)
from johnny_johnny_agent.capabilities.github.client import (
    get_viewer_project_by_title,
    list_project_issues,
)
from johnny_johnny_agent.capabilities.backlog_sync.purge import (
    purge_johnny_managed_issues,
)
from johnny_johnny_agent.capabilities.github.backlog_exporter import (
    generate_backlog_yaml_from_github_project,
)
from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    update_issue_status,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_writer import (
    save_backlog_yaml,
)
from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    update_issue_status,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_writer import (
    save_backlog_yaml,
)

DEFAULT_BACKLOG_PATH = "data/input/backlog/Backlog-as-Code-Synchronization-Epic.md"
DEFAULT_GITHUB_OWNER = "ggortsema"
DEFAULT_GITHUB_REPOSITORY = "styxcd-docs"
DEFAULT_GITHUB_PROJECT_TITLE = "MycroftAI Engineering Roadmap"


app = typer.Typer(
    help="Johnny-Johnny Agent CLI",
    no_args_is_help=True,
)

backlog_app = typer.Typer(
    help="Backlog commands",
    no_args_is_help=True,
)

app.add_typer(backlog_app, name="backlog")


@app.command()
def serve(
        host: Annotated[
            str,
            typer.Option(help="Host address for the API server."),
        ] = "127.0.0.1",
        port: Annotated[
            int,
            typer.Option(help="Port for the API server."),
        ] = 8000,
        reload: Annotated[
            bool,
            typer.Option(help="Reload the server when code changes."),
        ] = False,
) -> None:
    """Start the Johnny-Johnny API server."""
    uvicorn.run(
        "johnny_johnny_agent.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )

@backlog_app.command("generate")
def generate_backlog_yaml(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="GitHub ProjectV2 title."),
        ] = DEFAULT_GITHUB_PROJECT_TITLE,
        output: Annotated[
            str,
            typer.Option("--output", "-o", help="Path to write generated backlog YAML."),
        ] = "data/input/backlog/backlog.yml",
) -> None:
    """Generate canonical backlog YAML from the current GitHub ProjectV2."""
    generate_backlog_yaml_from_github_project(
        project_title=project,
        output_path=output,
    )

    typer.echo(f"Wrote canonical backlog YAML: {output}")

@backlog_app.command("publish")
def publish_backlog(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the Markdown backlog file."),
        ],
        repository: Annotated[
            str,
            typer.Option("--repository", "-r", help="GitHub repository name."),
        ],
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="GitHub ProjectV2 title."),
        ],
        owner: Annotated[
            str,
            typer.Option("--owner", "-o", help="GitHub repository owner."),
        ] = DEFAULT_GITHUB_OWNER,
) -> None:
    """Publish a Markdown backlog into GitHub ProjectV2."""
    typer.echo("Johnny-Johnny Agent")
    typer.echo()

    publish_backlog_from_markdown(
        backlog_path=file,
        owner=owner,
        repository_name=repository,
        project_title=project,
    )

@backlog_app.command("validate")
def validate_backlog(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ],
        schema: Annotated[
            str,
            typer.Option("--schema", "-s", help="Path to the JSON Schema file."),
        ] = "docs/schemas/backlog-v1.schema.json",
) -> None:
    """Validate a backlog YAML file against the v1 JSON Schema."""
    validate_backlog_yaml(
        backlog_path=file,
        schema_path=schema,
    )

@backlog_app.command("inspect")
def inspect_backlog(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ],
) -> None:
    """Inspect a canonical backlog YAML file."""
    backlog = load_backlog_yaml(file)

    issue_count = sum(len(epic.issues) for epic in backlog.epics)

    typer.echo(f"Project: {backlog.project.name}")
    typer.echo(f"Provider: {backlog.project.provider}")
    typer.echo(f"Epics: {len(backlog.epics)}")
    typer.echo(f"Issues: {issue_count}")

@backlog_app.command("preview-epic-body")
def preview_epic_body(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ],
        epic_id: Annotated[
            str,
            typer.Option("--epic-id", help="Canonical epic id."),
        ],
) -> None:
    """Preview the GitHub issue body for a canonical epic."""
    backlog = load_backlog_yaml(file)

    for epic in backlog.epics:
        if epic.id == epic_id:
            typer.echo(render_epic_body(epic))
            return

    raise RuntimeError(f"Epic not found: {epic_id}")

@backlog_app.command("reconcile")
def reconcile_backlog(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ],
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Show the reconciliation plan without making changes."),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option("--confirm", help="Execute the reconciliation plan."),
        ] = False,
) -> None:
    """Reconcile the configured provider from the canonical backlog."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)

    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to execute.")
        raise typer.Exit(code=1)

    backlog = load_backlog_yaml(file)
    github_project = get_viewer_project_by_title(backlog.project.title)
    current_project_issues = list_project_issues(github_project["id"])

    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=current_project_issues,
    )
    if dry_run:
        _print_reconciliation_plan(plan)
        return

    execute_reconciliation_plan(
        plan=plan,
        project_title=backlog.project.name,
    )

@backlog_app.command("pull")
def pull_backlog(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="GitHub ProjectV2 title."),
        ] = DEFAULT_GITHUB_PROJECT_TITLE,
) -> None:
    """Pull the current GitHub ProjectV2 projection as JSON."""
    github_project = get_viewer_project_by_title(project)
    issues = list_project_issues(github_project["id"])

    typer.echo(
        json.dumps(
            {
                "project": github_project,
                "issues": issues,
            },
            indent=2,
        )
    )

@backlog_app.command("update-issue")
def update_issue(
        issue_id: Annotated[
            str,
            typer.Argument(help="Stable Johnny-Johnny issue id."),
        ],
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ] = "data/input/backlog/backlog.yml",
        status: Annotated[
            str | None,
            typer.Option("--status", help="New project planning status."),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Preview reconciliation."),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option("--confirm", help="Save and reconcile."),
        ] = False,
) -> None:
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)

    if status is None:
        typer.echo("Nothing to update.")
        raise typer.Exit(code=1)

    backlog = load_backlog_yaml(file)

    issue = update_issue_status(
        backlog=backlog,
        issue_id=issue_id,
        status=status,
    )

    typer.echo(f"Updated: {issue.title}")
    typer.echo(f"Status: {issue.status}")

    if dry_run:
        plan = _plan_reconcile(backlog)
        _print_reconciliation_plan(plan)
        return

    save_backlog_yaml(
        backlog=backlog,
        backlog_path=file,
    )

    typer.echo(f"Saved: {file}")

    if confirm:
        plan = _plan_reconcile(backlog)

        _print_reconciliation_plan(plan)

        if plan.operations:
            execute_reconciliation_plan(
                plan=plan,
                project_title=backlog.project.title,
            )

@backlog_app.command("purge")
def purge_backlog_projection(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="GitHub ProjectV2 title."),
        ] = DEFAULT_GITHUB_PROJECT_TITLE,
        confirm: Annotated[
            bool,
            typer.Option("--confirm", help="Delete Johnny-managed GitHub issues."),
        ] = False,
) -> None:
    """Delete Johnny-managed issues from a GitHub ProjectV2 projection."""
    purge_johnny_managed_issues(
        project_title=project,
        confirm=confirm,
    )

def _plan_reconcile(backlog):
    github_project = get_viewer_project_by_title(backlog.project.title)

    current_project_issues = list_project_issues(
        github_project["id"],
    )

    return plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=current_project_issues,
    )

def _print_reconciliation_plan(plan) -> None:
    typer.echo("Execution Plan")
    typer.echo()

    if not plan.operations:
        typer.echo("No operations.")

    for operation in plan.operations:
        if isinstance(operation, CreateEpicOperation):
            typer.echo(f"+ Create epic: {operation.epic.title} [{operation.epic.id}]")

        elif isinstance(operation, CreateIssueOperation):
            typer.echo(
                f"+ Create issue: {operation.issue.title} "
                f"[{operation.issue.id}] "
                f"in {operation.issue.repository}"
            )

        elif isinstance(operation, AddIssueToProjectOperation):
            typer.echo(
                f"+ Add issue to project: {operation.issue.title}"
            )

        elif isinstance(operation, AttachIssueToEpicOperation):
            typer.echo(
                f"+ Attach issue to epic: {operation.issue.title} "
                f"-> {operation.parent_epic.title}"
            )

        elif isinstance(operation, UpdateIssueStatusOperation):
            typer.echo(
                f"+ Update issue status: "
                f"{operation.issue.title} "
                f"{operation.current_status} -> {operation.desired_status}"
        )

    typer.echo()
    typer.echo(f"Operations: {len(plan.operations)}")

