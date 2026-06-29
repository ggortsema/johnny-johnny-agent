from johnny_johnny_agent.capabilities.backlog_sync.loader import load_markdown
from johnny_johnny_agent.capabilities.backlog_sync.parser.markdown import parse_backlog
from johnny_johnny_agent.capabilities.github.client import (
    get_repository,
    get_viewer_project_by_title,
)
from johnny_johnny_agent.capabilities.github.publisher import publish_backlog


def publish_backlog_from_markdown(
        backlog_path: str,
        owner: str,
        repository_name: str,
        project_title: str,
) -> None:
    print("Loading backlog...")
    markdown = load_markdown(backlog_path)
    backlog = parse_backlog(markdown)

    print(f"Epics found: {len(backlog.epics)}")
    print()

    print("Resolving GitHub repository...")
    repository = get_repository(owner, repository_name)

    print("Resolving GitHub project...")
    project = get_viewer_project_by_title(project_title)

    print()

    publish_backlog(
        backlog=backlog,
        owner=owner,
        repository_name=repository_name,
        repository_id=repository["id"],
        project_id=project["id"],
    )