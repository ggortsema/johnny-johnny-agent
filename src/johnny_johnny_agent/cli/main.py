from typing import Annotated

import typer
import uvicorn

from johnny_johnny_agent.capabilities.backlog_sync.workflow import (
    publish_backlog_from_markdown,
)
from johnny_johnny_agent.capabilities.github.project_reader import print_project_issues

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


@backlog_app.command("pull")
def pull_backlog(
        project: Annotated[
            str,
            typer.Option("--project", "-p", help="GitHub ProjectV2 title."),
        ],
) -> None:
    """Read issues from a GitHub ProjectV2."""
    print_project_issues(project)