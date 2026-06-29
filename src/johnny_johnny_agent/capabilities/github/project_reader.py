from johnny_johnny_agent.capabilities.github.client import (
    get_viewer_project_by_title,
    list_project_issues,
)


def print_project_issues(project_title: str) -> None:
    project = get_viewer_project_by_title(project_title)
    issues = list_project_issues(project["id"])

    print(f"Project: {project['title']}")
    print(f"Issues found: {len(issues)}")
    print()

    for issue in issues:
        print(f"- #{issue['number']} {issue['title']}")