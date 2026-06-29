from johnny_johnny_agent.capabilities.github.client import (
    add_issue_to_project,
    add_sub_issue,
    create_issue,
    list_project_issue_titles,
)
from johnny_johnny_agent.domain.backlog import Backlog


def publish_backlog(
        backlog: Backlog,
        owner: str,
        repository_name: str,
        repository_id: str,
        project_id: str,
) -> None:
    existing_titles = list_project_issue_titles(project_id)

    print("Publishing backlog to GitHub")
    print()

    for epic in backlog.epics:
        parent_title = f"[Epic] {epic.title}"

        if parent_title in existing_titles:
            print(f"Skipping existing parent issue: {parent_title}")
            continue

        print(f"Creating parent issue: {parent_title}")
        parent_issue = create_issue(
            repository_id=repository_id,
            title=parent_title,
            body=epic.description,
        )

        add_issue_to_project(project_id, parent_issue["id"])

        print(f"Created parent issue #{parent_issue['number']}")
        print(f"URL: {parent_issue['url']}")
        print()

        for issue in epic.issues:
            if issue.title in existing_titles:
                print(f"  Skipping existing child issue: {issue.title}")
                continue

            print(f"  Creating child issue: {issue.title}")
            child_issue = create_issue(
                repository_id=repository_id,
                title=issue.title,
                body=issue.description,
            )

            add_issue_to_project(project_id, child_issue["id"])

            add_sub_issue(
                owner=owner,
                repo=repository_name,
                parent_issue_number=parent_issue["number"],
                child_issue_database_id=child_issue["databaseId"],
            )

            print(f"  Created child issue #{child_issue['number']}")
            print(f"  URL: {child_issue['url']}")

        print()