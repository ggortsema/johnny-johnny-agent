from johnny_johnny_agent.capabilities.github.client import (
    delete_issue,
    get_viewer_project_by_title,
    list_project_issues,
)


JOHNNY_METADATA_MARKER = "<!-- johnny-johnny"


def purge_johnny_managed_issues(
        project_title: str,
        confirm: bool,
) -> None:
    project = get_viewer_project_by_title(project_title)
    issues = list_project_issues(project["id"])

    johnny_issues = [
        issue
        for issue in issues
        if JOHNNY_METADATA_MARKER in issue["body"]
    ]

    print(f"Project: {project_title}")
    print(f"Johnny-managed issues found: {len(johnny_issues)}")
    print()

    for issue in johnny_issues:
        print(f"- #{issue['number']} {issue['title']}")

    if not confirm:
        print()
        print("Dry run only. Re-run with --confirm to delete these issues.")
        return

    print()

    for issue in reversed(johnny_issues):
        print(f"Deleting #{issue['number']} {issue['title']}")
        delete_issue(issue["id"])

    print()
    print("Done.")