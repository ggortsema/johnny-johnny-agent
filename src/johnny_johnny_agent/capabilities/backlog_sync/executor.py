from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    CreateCommentOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    DeleteIssueOperation,
    ExecutionPlan,
    UpdateIssueStatusOperation,
)
from johnny_johnny_agent.capabilities.github.client import (
    add_issue_to_project,
    add_sub_issue,
    create_issue,
    create_issue_comment,
    delete_issue as delete_github_issue,
    get_repository,
    get_viewer_project_by_title,
    update_project_item_status,
)
from johnny_johnny_agent.capabilities.github.renderer import (
    render_comment_body,
    render_epic_body,
    render_issue_body,
)


def execute_reconciliation_plan(
        plan: ExecutionPlan,
        project_title: str,
        project_id: str | None = None,
        announce: bool = True,
) -> None:
    resolved_project_id = project_id
    if resolved_project_id is None:
        project = get_viewer_project_by_title(project_title)
        resolved_project_id = project["id"]

    repositories: dict[str, dict] = {}
    created_epics: dict[str, dict] = {}
    created_issues: dict[str, dict] = {}

    if announce:
        print(f"Reconciling GitHub project: {project_title}")
        print()

    for operation in plan.operations:
        if isinstance(operation, CreateEpicOperation):
            epic = operation.epic
            repository = _get_repository(epic.repository, repositories)

            title = f"[Epic] {epic.title}"
            body = render_epic_body(epic)

            print(f"Creating epic: {title}")

            issue = create_issue(
                repository_id=repository["id"],
                title=title,
                body=body,
            )

            _hydrate_github_metadata(
                item=epic,
                issue=issue,
            )

            project_item = add_issue_to_project(resolved_project_id, issue["id"])

            _hydrate_github_metadata(
                item=epic,
                issue=issue,
                project_item=project_item,
            )

            created_epics[epic.id] = issue

            print(f"Created epic #{issue['number']}")
            print(f"URL: {issue['url']}")
            print()

        elif isinstance(operation, CreateIssueOperation):
            issue_model = operation.issue
            repository = _get_repository(issue_model.repository, repositories)

            title = issue_model.title
            body = render_issue_body(
                issue=issue_model,
                parent_epic=operation.parent_epic,
            )

            print(f"Creating issue: {title}")

            issue = create_issue(
                repository_id=repository["id"],
                title=title,
                body=body,
            )

            _hydrate_github_metadata(
                item=issue_model,
                issue=issue,
            )

            created_issues[issue_model.id] = issue

            print(f"Created issue #{issue['number']}")
            print(f"URL: {issue['url']}")
            print()

        elif isinstance(operation, AddIssueToProjectOperation):
            issue_model = operation.issue
            issue = _get_created_issue(issue_model.id, created_issues)

            print(f"Adding issue to project: {issue_model.title}")

            project_item = add_issue_to_project(resolved_project_id, issue["id"])

            _hydrate_github_metadata(
                item=issue_model,
                issue=issue,
                project_item=project_item,
            )

            print("Added to project.")
            print()

        elif isinstance(operation, AttachIssueToEpicOperation):
            epic = operation.parent_epic
            issue_model = operation.issue

            parent_issue = _get_epic_issue(
                epic=epic,
                created_epics=created_epics,
            )
            child_issue = _get_created_issue(issue_model.id, created_issues)

            owner, repo = issue_model.repository.split("/", maxsplit=1)

            print(f"Attaching issue to epic: {issue_model.title} -> {epic.title}")

            add_sub_issue(
                owner=owner,
                repo=repo,
                parent_issue_number=parent_issue["number"],
                child_issue_database_id=child_issue["databaseId"],
            )

            print("Attached to epic.")
            print()

        elif isinstance(operation, UpdateIssueStatusOperation):
            issue_model = operation.issue
            project_item_id = _get_project_item_id(issue_model)

            print(
                f"Updating issue status: {issue_model.title} "
                f"{operation.current_status} -> {operation.desired_status}"
            )

            update_project_item_status(
                project_id=resolved_project_id,
                project_item_id=project_item_id,
                status=operation.desired_status,
            )

            print("Status updated.")
            print()

        elif isinstance(operation, CreateCommentOperation):
            item = operation.item
            comment_model = operation.comment

            github_issue = _get_github_issue_for_item(
                item=item,
                created_epics=created_epics,
                created_issues=created_issues,
            )

            print(f"Creating comment on {item.type}: {item.title}")
            print(f"Comment: {comment_model.id}")

            github_comment = create_issue_comment(
                issue_id=github_issue["id"],
                body=render_comment_body(
                    item=item,
                    comment=comment_model,
                ),
            )

            _hydrate_github_comment_metadata(
                comment=comment_model,
                github_comment=github_comment,
            )

            print("Comment created.")
            print(f"URL: {github_comment['url']}")
            print()

        elif isinstance(operation, DeleteIssueOperation):
            issue_model = operation.issue
            issue_id = _get_issue_id(issue_model)

            print(f"Deleting issue: {issue_model.title} [{issue_model.id}]")

            delete_github_issue(issue_id)

            print("Deleted.")
            print()


def _hydrate_github_metadata(
        item,
        issue: dict,
        project_item: dict | None = None,
) -> None:
    current_github_metadata = item.provider_metadata.get("github", {})

    github_metadata = {
        **current_github_metadata,
        "issue_id": issue.get("id") or issue.get("issue_id"),
        "database_id": issue.get("databaseId") or issue.get("database_id"),
        "number": issue.get("number"),
        "url": issue.get("url"),
    }

    if project_item:
        github_metadata["project_item_id"] = (
                project_item.get("id")
                or project_item.get("project_item_id")
        )

    item.provider_metadata["github"] = {
        key: value
        for key, value in github_metadata.items()
        if value is not None
    }


def _hydrate_github_comment_metadata(
        comment,
        github_comment: dict,
) -> None:
    current_github_metadata = comment.provider_metadata.get("github", {})

    github_metadata = {
        **current_github_metadata,
        "comment_id": github_comment.get("id") or github_comment.get("comment_id"),
        "database_id": github_comment.get("databaseId") or github_comment.get("database_id"),
        "url": github_comment.get("url"),
        "created_at": github_comment.get("createdAt") or github_comment.get("created_at"),
        "updated_at": github_comment.get("updatedAt") or github_comment.get("updated_at"),
    }

    comment.provider_metadata["github"] = {
        key: value
        for key, value in github_metadata.items()
        if value is not None
    }


def _get_github_issue_for_item(
        item,
        created_epics: dict[str, dict],
        created_issues: dict[str, dict],
) -> dict:
    if item.type == "epic" and item.id in created_epics:
        return created_epics[item.id]

    if item.type == "issue" and item.id in created_issues:
        return created_issues[item.id]

    github_metadata = item.provider_metadata.get("github", {})
    issue_id = github_metadata.get("issue_id")

    if not issue_id:
        raise RuntimeError(
            f"Cannot create comment because issue_id is missing: {item.id}"
        )

    return {
        "id": issue_id,
        "number": github_metadata.get("number"),
        "url": github_metadata.get("url"),
    }


def _get_project_item_id(issue_model) -> str:
    project_item_id = (
        issue_model.provider_metadata
        .get("github", {})
        .get("project_item_id")
    )

    if not project_item_id:
        raise RuntimeError(
            f"Cannot update issue status because project_item_id is missing: {issue_model.id}"
        )

    return project_item_id


def _get_issue_id(issue_model) -> str:
    issue_id = (
        issue_model.provider_metadata
        .get("github", {})
        .get("issue_id")
    )

    if not issue_id:
        raise RuntimeError(
            f"Cannot delete issue because issue_id is missing: {issue_model.id}"
        )

    return issue_id


def _get_epic_issue(
        epic,
        created_epics: dict[str, dict],
) -> dict:
    if epic.id in created_epics:
        return created_epics[epic.id]

    github_metadata = epic.provider_metadata.get("github", {})

    number = github_metadata.get("number")
    if not number:
        raise RuntimeError(
            f"Cannot attach issue to epic because epic issue number is missing: {epic.id}"
        )

    return {
        "number": number,
    }


def _get_created_issue(
        issue_id: str,
        created_issues: dict[str, dict],
) -> dict:
    if issue_id not in created_issues:
        raise RuntimeError(
            f"Cannot operate on issue because it was not created in this execution: {issue_id}"
        )

    return created_issues[issue_id]


def _get_repository(
        repository_name_with_owner: str,
        repositories: dict[str, dict],
) -> dict:
    if repository_name_with_owner in repositories:
        return repositories[repository_name_with_owner]

    owner, name = repository_name_with_owner.split("/", maxsplit=1)
    repository = get_repository(owner, name)
    repositories[repository_name_with_owner] = repository

    return repository