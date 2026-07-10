from typing import Annotated

import json
import typer
import uvicorn

# Import for startup side effect: loads .env configuration.
import johnny_johnny_agent.config

from johnny_johnny_agent.capabilities.backlog_persistence.workflow import (
    BacklogPurgeResult,
    check_postgres_backlog_database,
    create_epic_in_postgres,
    create_issue_in_postgres,
    delete_issue_in_postgres,
    export_backlog_yaml_from_postgres,
    import_backlog_yaml_to_postgres,
    load_backlog_from_postgres,
    move_issue_in_postgres,
    preview_delete_issue_in_postgres,
    preview_create_epic_in_postgres,
    preview_create_issue_in_postgres,
    preview_move_issue_in_postgres,
    preview_purge_backlog_projection,
    preview_reconcile_backlog_from_postgres,
    preview_update_item_in_postgres,
    purge_backlog_projection_from_postgres,
    reconcile_backlog_from_postgres,
    summarize_backlog,
    update_item_in_postgres,
)
from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    find_backlog_item,
    find_epic_issues,
)
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    DeleteIssueOperation,
    UpdateIssueStatusOperation,
    CreateCommentOperation,
)
from johnny_johnny_agent.capabilities.backlog_sync.renderers import (
    get_backlog_resource_renderer,
)
from johnny_johnny_agent.capabilities.backlog_sync.validator import (
    validate_backlog_yaml,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_loader import load_backlog_yaml
from johnny_johnny_agent.capabilities.github.backlog_exporter import (
    generate_backlog_yaml_from_github_project,
)
from johnny_johnny_agent.capabilities.github.client import (
    get_viewer_project_by_title,
    list_project_issues,
)

DEFAULT_GITHUB_PROJECT_TITLE = "MycroftAI Engineering Roadmap"


app = typer.Typer(
    help="Johnny-Johnny Agent CLI",
    no_args_is_help=True,
)

backlog_app = typer.Typer(
    help="Backlog commands",
    no_args_is_help=True,
)

backlog_create_app = typer.Typer(
    help="Create backlog objects",
    no_args_is_help=True,
)

backlog_list_app = typer.Typer(
    help="List backlog objects",
    no_args_is_help=True,
)

backlog_database_app = typer.Typer(
    help="PostgreSQL canonical backlog persistence commands",
    no_args_is_help=True,
)

maintenance_app = typer.Typer(
    help="Maintenance and development commands",
    no_args_is_help=True,
)

app.add_typer(maintenance_app, name="maintenance")
app.add_typer(backlog_app, name="backlog")
backlog_app.add_typer(backlog_create_app, name="create")
backlog_app.add_typer(backlog_list_app, name="list")
backlog_app.add_typer(backlog_database_app, name="db")


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


# TODO: Replace this file-oriented command with a renamed GitHub-to-PostgreSQL
# import workflow after durable, rate-limited provider reconciliation is implemented.
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
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
) -> None:
    """Inspect a canonical backlog directly from PostgreSQL."""
    _inspect_backlog(
        project=project,
        provider=provider,
        provider_account_username=provider_account_username,
        database_url=database_url,
    )


@backlog_database_app.command("check")
def check_backlog_database(
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
) -> None:
    """Check connectivity and canonical backlog schema readiness."""
    try:
        status = check_postgres_backlog_database(database_url=database_url)
    except Exception as ex:
        typer.echo("PostgreSQL connection: FAILED")
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo("PostgreSQL connection: OK")
    typer.echo(f"Database: {status.database}")
    typer.echo(f"User: {status.database_user}")
    typer.echo(f"Server version: {status.server_version}")
    typer.echo(f"Schema: {status.schema}")
    typer.echo(
        "Canonical tables: "
        f"{status.present_expected_table_count}/{status.expected_table_count}"
    )
    typer.echo(f"Seeded providers: {status.provider_count}")

    if not status.ready:
        if status.missing_tables:
            typer.echo(f"Missing tables: {', '.join(status.missing_tables)}")
        if status.provider_count == 0:
            typer.echo("Seeded providers: missing")
        typer.echo("Canonical backlog persistence: not ready")
        raise typer.Exit(code=1)

    typer.echo("Canonical backlog persistence: ready")


@backlog_database_app.command("import")
def import_backlog_database(
        file: Annotated[
            str,
            typer.Option("--file", "-f", help="Path to the backlog YAML file."),
        ] = "data/input/backlog/backlog-sandbox.yml",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        user_display_name: Annotated[
            str,
            typer.Option("--user-display-name", help="Canonical user display name."),
        ] = "Grant Gortsema",
        user_primary_email: Annotated[
            str | None,
            typer.Option("--user-email", help="Canonical user email, when known."),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Inspect the replacement without connecting."),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option("--confirm", help="Replace the selected project snapshot."),
        ] = False,
) -> None:
    """Replace one canonical PostgreSQL backlog snapshot from YAML."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)

    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to import.")
        raise typer.Exit(code=1)

    try:
        backlog = load_backlog_yaml(file)
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    summary = summarize_backlog(backlog)
    typer.echo("Mode: transactional snapshot replacement")
    typer.echo(f"File: {file}")
    typer.echo(
        f"Project: {backlog.project.provider} / {provider_account_username} / {backlog.project.title}"
    )
    typer.echo(f"Epics: {summary.epic_count}")
    typer.echo(f"Issues: {summary.issue_count}")
    typer.echo(f"Acceptance criteria: {summary.acceptance_criterion_count}")
    typer.echo(f"Comments: {summary.comment_count}")
    typer.echo(f"Labels: {summary.label_count}")
    typer.echo(f"Assignees: {summary.assignee_count}")

    if dry_run:
        typer.echo("No database changes made.")
        return

    try:
        result = import_backlog_yaml_to_postgres(
            backlog_path=file,
            database_url=database_url,
            user_display_name=user_display_name,
            user_primary_email=user_primary_email,
            provider_account_username=provider_account_username,
            provider_account_display_name=user_display_name,
            verify=True,
        )
    except Exception as ex:
        typer.echo(f"PostgreSQL import failed: {ex}")
        raise typer.Exit(code=1)

    typer.echo("Imported canonical backlog into PostgreSQL.")
    typer.echo(f"Project: {result.location.describe()}")
    typer.echo(f"Epics: {result.epic_count}")
    typer.echo(f"Issues: {result.issue_count}")
    typer.echo(f"Round-trip verified: {'yes' if result.verified else 'no'}")


@backlog_database_app.command("export")
def export_backlog_database(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        output: Annotated[
            str,
            typer.Option("--output", "-o", help="Path to write exported backlog YAML."),
        ] = "data/output/backlog-from-db.yml",
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
) -> None:
    """Export one canonical PostgreSQL backlog snapshot to YAML."""
    try:
        result = export_backlog_yaml_from_postgres(
            output_path=output,
            provider_project_title=project,
            provider=provider,
            provider_account_username=provider_account_username,
            database_url=database_url,
        )
    except Exception as ex:
        typer.echo(f"PostgreSQL export failed: {ex}")
        raise typer.Exit(code=1)

    typer.echo("Exported canonical backlog from PostgreSQL.")
    typer.echo(f"Project: {result.location.describe()}")
    typer.echo(f"Epics: {result.epic_count}")
    typer.echo(f"Issues: {result.issue_count}")
    typer.echo(f"Comments: {result.comment_count}")
    typer.echo(f"Wrote: {result.output_path}")


@backlog_app.command("describe")
def describe_backlog_item(
        item_id: Annotated[
            str,
            typer.Argument(help="Stable Johnny-Johnny backlog item id."),
        ],
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        output: Annotated[
            str,
            typer.Option("--output", "-o", help="Output format: human, yaml, json."),
        ] = "human",
) -> None:
    """Describe a canonical backlog item directly from PostgreSQL."""
    _describe_backlog_item(
        item_id=item_id,
        project=project,
        provider=provider,
        provider_account_username=provider_account_username,
        database_url=database_url,
        output=output,
    )

@backlog_app.command("reconcile")
def reconcile_backlog(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        max_operations: Annotated[
            int | None,
            typer.Option(
                "--max-operations",
                min=1,
                help=(
                    "Soft provider-operation budget. Complete item groups are "
                    "never split. Defaults to 100 unless --all is used."
                ),
            ),
        ] = None,
        all_operations: Annotated[
            bool,
            typer.Option(
                "--all",
                help="Execute every currently planned reconciliation operation.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview the selected reconciliation scope.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Execute the selected reconciliation scope.",
            ),
        ] = False,
) -> None:
    """Reconcile PostgreSQL canonical state to the bound provider project."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to execute.")
        raise typer.Exit(code=1)
    if all_operations and max_operations is not None:
        typer.echo("Use either --all or --max-operations, not both.")
        raise typer.Exit(code=1)

    operation_limit = None if all_operations else (max_operations or 100)

    try:
        if dry_run:
            preview = preview_reconcile_backlog_from_postgres(
                provider=provider,
                provider_account_username=provider_account_username,
                provider_project_title=project,
                max_operations=operation_limit,
                database_url=database_url,
            )
            _print_reconciliation_plan(preview.execution_plan)
            typer.echo()
            typer.echo(f"Total operations: {preview.total_operation_count}")
            typer.echo(
                f"Operations selected: {preview.execution_operation_count}"
            )
            typer.echo(
                f"Operations remaining after selection: "
                f"{preview.remaining_operation_count}"
            )
            typer.echo("No PostgreSQL or GitHub changes made.")
            return

        result = reconcile_backlog_from_postgres(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            max_operations=operation_limit,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(
        "Reconciliation complete."
        if all_operations
        else "Reconciliation chunk complete."
    )
    typer.echo(f"Operation groups executed: {result.executed_group_count}")
    typer.echo(
        f"Provider operations executed: "
        f"{result.preview.execution_operation_count}"
    )
    typer.echo(
        f"Provider metadata hydrated: {result.hydrated_item_count} canonical items"
    )
    typer.echo(
        f"Operations remaining: {result.preview.remaining_operation_count}"
    )
    if result.preview.remaining_operation_count:
        typer.echo("Rerun the same command to continue reconciliation.")
    else:
        typer.echo("Canonical and provider state reconciled.")


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


@backlog_create_app.command("issue")
def create_backlog_issue(
        epic: Annotated[
            str,
            typer.Option("--epic", help="Parent epic id."),
        ],
        title: Annotated[
            str,
            typer.Option("--title", "-t", help="Issue title."),
        ],
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        issue_id: Annotated[
            str | None,
            typer.Option(
                "--id",
                help="Stable Johnny-Johnny issue id. Defaults to a slugified title.",
            ),
        ] = None,
        description: Annotated[
            str,
            typer.Option("--description", "-d", help="Issue description."),
        ] = "",
        repository: Annotated[
            str | None,
            typer.Option(
                "--repository",
                "-r",
                help="Repository name with owner. Defaults to parent epic repository.",
            ),
        ] = None,
        acceptance: Annotated[
            list[str] | None,
            typer.Option(
                "--acceptance",
                help="Acceptance criterion. Can be repeated.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview without changing PostgreSQL or GitHub.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Create the canonical issue and GitHub projection.",
            ),
        ] = False,
) -> None:
    """Create one canonical issue and immediately project it to GitHub."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to create the issue.")
        raise typer.Exit(code=1)

    try:
        if dry_run:
            issue = preview_create_issue_in_postgres(
                provider=provider,
                provider_account_username=provider_account_username,
                provider_project_title=project,
                parent_epic_id=epic,
                title=title,
                issue_id=issue_id,
                description=description,
                repository_name=repository,
                acceptance_criteria=acceptance or [],
                database_url=database_url,
            )
            parent_epic_id = epic
        else:
            issue, parent_epic = create_issue_in_postgres(
                provider=provider,
                provider_account_username=provider_account_username,
                provider_project_title=project,
                parent_epic_id=epic,
                title=title,
                issue_id=issue_id,
                description=description,
                repository_name=repository,
                acceptance_criteria=acceptance or [],
                database_url=database_url,
            )
            parent_epic_id = parent_epic.id
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(
        f"{'Canonical issue preview' if dry_run else 'Synchronized canonical issue'}: "
        f"{issue.title}"
    )
    typer.echo(f"ID: {issue.id}")
    typer.echo(f"Epic: {parent_epic_id}")
    typer.echo(f"Status: {issue.status}")
    typer.echo(f"Repository: {issue.repository}")
    typer.echo(f"Order: {issue.order}")

    if dry_run:
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    github_metadata = issue.provider_metadata.get("github", {})
    typer.echo(f"Project: {provider} / {provider_account_username} / {project}")
    typer.echo(f"GitHub issue: #{github_metadata.get('number')}")
    typer.echo(f"GitHub URL: {github_metadata.get('url')}")
    typer.echo("Canonical and provider state committed.")


@backlog_app.command("update")
def update_backlog_item(
        item_id: Annotated[
            str,
            typer.Argument(help="Stable Johnny-Johnny backlog item id."),
        ],
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        title: Annotated[
            str | None,
            typer.Option("--title", "-t", help="New title. Replaces the current title."),
        ] = None,
        description: Annotated[
            str | None,
            typer.Option(
                "--description",
                "-d",
                help="New description prose. Replaces the current description.",
            ),
        ] = None,
        status: Annotated[
            str | None,
            typer.Option("--status", help="New project planning status."),
        ] = None,
        acceptance: Annotated[
            list[str] | None,
            typer.Option(
                "--acceptance",
                help="Acceptance criterion. Can be repeated. Replaces the full list.",
            ),
        ] = None,
        comment: Annotated[
            str | None,
            typer.Option("--comment", help="Comment to append to the backlog item."),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview without changing PostgreSQL or GitHub.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Update the canonical item and GitHub projection.",
            ),
        ] = False,
) -> None:
    """Update one canonical epic or issue and its GitHub projection."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to update the item.")
        raise typer.Exit(code=1)
    if not any(value is not None for value in [title, description, status, acceptance, comment]):
        typer.echo("Nothing to update.")
        raise typer.Exit(code=1)

    workflow = preview_update_item_in_postgres if dry_run else update_item_in_postgres
    try:
        item = workflow(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            item_id=item_id,
            title=title,
            description=description,
            status=status,
            acceptance_criteria=acceptance,
            comment=comment,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(
        f"{'Canonical update preview' if dry_run else 'Synchronized canonical'} "
        f"{item.type}: {item.title}"
    )
    typer.echo(f"ID: {item.id}")
    typer.echo(f"Status: {item.status}")
    if title is not None:
        typer.echo("Title: updated")
    if description is not None:
        typer.echo("Description: updated")
    if acceptance is not None:
        typer.echo(f"Acceptance criteria: replaced with {len(item.acceptance_criteria)} item(s)")
    if comment is not None:
        typer.echo(f"Comments: {len(item.comments)}")

    if dry_run:
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    github_metadata = item.provider_metadata.get("github", {})
    typer.echo(f"GitHub issue: #{github_metadata.get('number')}")
    typer.echo(f"GitHub URL: {github_metadata.get('url')}")
    typer.echo("Canonical and provider state committed.")


@backlog_app.command("move")
def move_backlog_issue(
        issue_id: Annotated[
            str,
            typer.Argument(help="Stable Johnny-Johnny issue id."),
        ],
        to_epic: Annotated[
            str,
            typer.Option("--to-epic", help="Target parent epic id."),
        ],
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview without changing PostgreSQL or GitHub.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Move the canonical issue and GitHub parent relationship.",
            ),
        ] = False,
) -> None:
    """Move one canonical issue to a different epic and GitHub parent."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to move the issue.")
        raise typer.Exit(code=1)

    workflow = preview_move_issue_in_postgres if dry_run else move_issue_in_postgres
    try:
        issue, source_epic, target_epic = workflow(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            issue_id=issue_id,
            target_epic_id=to_epic,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(
        f"{'Canonical move preview' if dry_run else 'Synchronized canonical issue'}: "
        f"{issue.title}"
    )
    typer.echo(f"ID: {issue.id}")
    typer.echo(f"From epic: {source_epic.id}")
    typer.echo(f"To epic: {target_epic.id}")
    typer.echo(f"Repository: {issue.repository}")

    if dry_run:
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    github_metadata = issue.provider_metadata.get("github", {})
    typer.echo(f"GitHub issue: #{github_metadata.get('number')}")
    typer.echo(f"GitHub URL: {github_metadata.get('url')}")
    typer.echo("Canonical and provider state committed.")


@backlog_create_app.command("epic")
def create_backlog_epic(
        title: Annotated[
            str,
            typer.Option("--title", "-t", help="Epic title."),
        ],
        repository: Annotated[
            str,
            typer.Option("--repository", "-r", help="Repository name with owner."),
        ],
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        epic_id: Annotated[
            str | None,
            typer.Option(
                "--id",
                help="Stable Johnny-Johnny epic id. Defaults to a slugified title.",
            ),
        ] = None,
        description: Annotated[
            str,
            typer.Option("--description", "-d", help="Epic description."),
        ] = "",
        acceptance: Annotated[
            list[str] | None,
            typer.Option(
                "--acceptance",
                help="Acceptance criterion. Can be repeated.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview without changing PostgreSQL or GitHub.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Create the canonical epic and GitHub projection.",
            ),
        ] = False,
) -> None:
    """Create one canonical epic and immediately project it to GitHub."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)

    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to create the epic.")
        raise typer.Exit(code=1)

    create_workflow = (
        preview_create_epic_in_postgres
        if dry_run
        else create_epic_in_postgres
    )

    try:
        epic = create_workflow(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            title=title,
            repository_name=repository,
            epic_id=epic_id,
            description=description,
            acceptance_criteria=acceptance or [],
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    if dry_run:
        typer.echo(f"Canonical epic preview: {epic.title}")
    else:
        typer.echo(f"Synchronized canonical epic: {epic.title}")

    typer.echo(f"ID: {epic.id}")
    typer.echo(f"Status: {epic.status}")
    typer.echo(f"Repository: {epic.repository}")
    typer.echo(f"Order: {epic.order}")

    if dry_run:
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    github_metadata = epic.provider_metadata.get("github", {})
    typer.echo(f"Project: {provider} / {provider_account_username} / {project}")
    typer.echo(f"GitHub issue: #{github_metadata.get('number')}")
    typer.echo(f"GitHub URL: {github_metadata.get('url')}")
    typer.echo("Canonical and provider state committed.")


@backlog_list_app.command("epics")
def list_backlog_epics(
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        output: Annotated[
            str,
            typer.Option("--output", "-o", help="Output format: human, yaml, json."),
        ] = "human",
) -> None:
    """List canonical epics directly from PostgreSQL."""
    _list_backlog_epics(
        project=project,
        provider=provider,
        provider_account_username=provider_account_username,
        database_url=database_url,
        output=output,
    )


@backlog_list_app.command("items")
def list_backlog_items(
        project: Annotated[
            str,
            typer.Option(
                "--project",
                "-p",
                help="Canonical provider project title.",
            ),
        ],
        epic_id: Annotated[
            str | None,
            typer.Option("--epic", help="Parent epic id."),
        ] = None,
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        status: Annotated[
            list[str] | None,
            typer.Option("--status", help="Status to include. Can be repeated."),
        ] = None,
        exclude_status: Annotated[
            list[str] | None,
            typer.Option("--exclude-status", help="Status to exclude. Can be repeated."),
        ] = None,
        output: Annotated[
            str,
            typer.Option("--output", "-o", help="Output format: human, yaml, json."),
        ] = "human",
) -> None:
    """List canonical backlog items directly from PostgreSQL."""
    _list_backlog_items(
        project=project,
        epic_id=epic_id,
        provider=provider,
        provider_account_username=provider_account_username,
        database_url=database_url,
        status=status,
        exclude_status=exclude_status,
        output=output,
    )

@maintenance_app.command("delete-issue")
def delete_backlog_issue(
        issue_id: Annotated[
            str,
            typer.Argument(help="Stable Johnny-Johnny issue id."),
        ],
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview without changing PostgreSQL or GitHub.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Delete the canonical issue and GitHub projection.",
            ),
        ] = False,
) -> None:
    """Delete one canonical issue and its targeted GitHub projection."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to delete the issue.")
        raise typer.Exit(code=1)

    workflow = (
        preview_delete_issue_in_postgres
        if dry_run
        else delete_issue_in_postgres
    )
    try:
        result = workflow(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            issue_id=issue_id,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(
        f"{'Canonical deletion preview' if dry_run else 'Deleted canonical issue'}: "
        f"{result.issue.title}"
    )
    typer.echo(f"ID: {result.issue.id}")
    typer.echo(f"Epic: {result.parent_epic.id}")
    github_metadata = result.issue.provider_metadata.get("github", {})
    if github_metadata.get("number") is not None:
        typer.echo(f"GitHub issue: #{github_metadata['number']}")

    if dry_run:
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    typer.echo(
        "GitHub projection: deleted"
        if result.github_issue_deleted
        else "GitHub projection: already absent"
    )
    typer.echo("Canonical and provider deletion committed.")


@maintenance_app.command("purge")
def purge_backlog_projection(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="Canonical provider project title."),
        ],
        provider: Annotated[
            str,
            typer.Option("--provider", help="Provider key."),
        ] = "github",
        provider_account_username: Annotated[
            str,
            typer.Option(
                "--provider-account",
                help="Provider account username that owns the project.",
            ),
        ] = "ggortsema",
        database_url: Annotated[
            str | None,
            typer.Option(
                "--database-url",
                help="PostgreSQL connection string. Defaults to DATABASE_URL.",
            ),
        ] = None,
        max_issues: Annotated[
            int | None,
            typer.Option(
                "--max-issues",
                min=1,
                help=(
                    "Maximum GitHub issues to delete in this run. Defaults to "
                    "50 unless --all is used."
                ),
            ),
        ] = None,
        all_issues: Annotated[
            bool,
            typer.Option(
                "--all",
                help="Delete every Johnny-Johnny-managed issue in the projection.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Preview the selected GitHub purge scope.",
            ),
        ] = False,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm",
                help="Delete the selected GitHub projection scope.",
            ),
        ] = False,
) -> None:
    """Purge the provider projection while preserving canonical PostgreSQL data."""
    if dry_run and confirm:
        typer.echo("Use either --dry-run or --confirm, not both.")
        raise typer.Exit(code=1)
    if not dry_run and not confirm:
        typer.echo("Use --dry-run to preview or --confirm to purge the projection.")
        raise typer.Exit(code=1)
    if all_issues and max_issues is not None:
        typer.echo("Use either --all or --max-issues, not both.")
        raise typer.Exit(code=1)

    issue_limit = None if all_issues else (max_issues or 50)
    selected_workflow = (
        preview_purge_backlog_projection
        if dry_run
        else purge_backlog_projection_from_postgres
    )
    try:
        result = selected_workflow(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            max_issues=issue_limit,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    _print_purge_result(result)
    if dry_run:
        typer.echo()
        typer.echo("No PostgreSQL or GitHub changes made.")
        return

    typer.echo()
    typer.echo(f"GitHub issues deleted: {result.deleted_issue_count}")
    typer.echo(f"GitHub issues remaining: {result.remaining_issue_count}")
    if result.projection_metadata_cleared:
        typer.echo(f"Canonical items retained: {result.cleared_item_count}")
        typer.echo("Canonical provider metadata cleared.")
    else:
        typer.echo("Canonical provider metadata retained until the final purge chunk.")
        typer.echo("Rerun the same command to continue the purge.")


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

        elif isinstance(operation, CreateCommentOperation):
            typer.echo(
                f"+ Create comment: "
                f"{operation.item.title} "
                f"[{operation.comment.id}]"
            )

        elif isinstance(operation, DeleteIssueOperation):
            typer.echo(
                f"- Delete issue: {operation.issue.title} [{operation.issue.id}]"
            )

    typer.echo()
    typer.echo(f"Operations: {len(plan.operations)}")


def _print_purge_result(result: BacklogPurgeResult) -> None:
    typer.echo(f"Project: {result.project_title}")
    typer.echo(f"Johnny-managed GitHub issues found: {result.total_issue_count}")
    typer.echo(f"Issues in next purge chunk: {len(result.issues)}")
    for issue in result.issues:
        typer.echo(f"- #{issue.get('number')} {issue.get('title')}")

def _inspect_backlog(
        *,
        project: str,
        provider: str,
        provider_account_username: str,
        database_url: str | None,
) -> None:
    try:
        backlog = load_backlog_from_postgres(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            database_url=database_url,
        )
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    issue_count = sum(len(epic.issues) for epic in backlog.epics)

    typer.echo(f"Project: {backlog.project.title}")
    typer.echo(f"Provider: {backlog.project.provider}")
    typer.echo(f"Epics: {len(backlog.epics)}")
    typer.echo(f"Issues: {issue_count}")


def _describe_backlog_item(
        *,
        item_id: str,
        project: str,
        provider: str,
        provider_account_username: str,
        database_url: str | None,
        output: str,
) -> None:
    try:
        backlog = load_backlog_from_postgres(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            database_url=database_url,
        )
        item = find_backlog_item(backlog, item_id)
        renderer = get_backlog_resource_renderer(output)
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    typer.echo(renderer(backlog, item))


def _list_backlog_epics(
        *,
        project: str,
        provider: str,
        provider_account_username: str,
        database_url: str | None,
        output: str,
) -> None:
    try:
        backlog = load_backlog_from_postgres(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            database_url=database_url,
        )
        renderer = get_backlog_resource_renderer(output)
    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    epics = sorted(backlog.epics, key=lambda item: item.order)
    summaries = _to_backlog_item_summaries(epics)

    typer.echo(renderer(backlog, summaries))


def _list_backlog_items(
        *,
        project: str,
        epic_id: str | None,
        provider: str,
        provider_account_username: str,
        database_url: str | None,
        status: list[str] | None,
        exclude_status: list[str] | None,
        output: str,
) -> None:
    if status and exclude_status:
        typer.echo("Use either --status or --exclude-status, not both.")
        raise typer.Exit(code=1)

    try:
        backlog = load_backlog_from_postgres(
            provider=provider,
            provider_account_username=provider_account_username,
            provider_project_title=project,
            database_url=database_url,
        )

        if epic_id is not None:
            issues = find_epic_issues(
                backlog=backlog,
                epic_id=epic_id,
                statuses=status,
                excluded_statuses=exclude_status,
            )

        else:
            issues = []

            for epic in sorted(backlog.epics, key=lambda item: item.order):
                issues.extend(
                    find_epic_issues(
                        backlog=backlog,
                        epic_id=epic.id,
                        statuses=status,
                        excluded_statuses=exclude_status,
                    )
                )

        renderer = get_backlog_resource_renderer(output)

    except RuntimeError as ex:
        typer.echo(str(ex))
        raise typer.Exit(code=1)

    summaries = _to_backlog_item_summaries(issues)

    typer.echo(renderer(backlog, summaries))

def _to_backlog_item_summaries(items) -> list[dict[str, str]]:
    return [
        {
            "status": item.status,
            "id": item.id,
            "title": item.title,
        }
        for item in items
    ]