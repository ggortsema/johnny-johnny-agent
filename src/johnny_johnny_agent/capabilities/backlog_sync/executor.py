from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    ExecutionPlan,
    UpdateIssueStatusOperation,
)
from johnny_johnny_agent.capabilities.github.client import (
    add_issue_to_project,
    add_sub_issue,
    create_issue,
    get_repository,
    get_viewer_project_by_title,
    update_project_item_status,
)
from johnny_johnny_agent.capabilities.github.renderer import (
    render_epic_body,
    render_issue_body,
)


def execute_reconciliation_plan(
        plan: ExecutionPlan,
        project_title: str,
) -> None:
    project = get_viewer_project_by_title(project_title)
    project_id = project["id"]

    repositories: dict[str, dict] = {}
    created_epics: dict[str, dict] = {}
    created_issues: dict[str, dict] = {}

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

            add_issue_to_project(project_id, issue["id"])
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

            created_issues[issue_model.id] = issue

            print(f"Created issue #{issue['number']}")
            print(f"URL: {issue['url']}")
            print()

        elif isinstance(operation, AddIssueToProjectOperation):
            issue_model = operation.issue
            issue = _get_created_issue(issue_model.id, created_issues)

            print(f"Adding issue to project: {issue_model.title}")

            add_issue_to_project(project_id, issue["id"])

            print("Added to project.")
            print()

        elif isinstance(operation, AttachIssueToEpicOperation):
            epic = operation.parent_epic
            issue_model = operation.issue

            parent_issue = _get_created_epic(epic.id, created_epics)
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
                project_id=project_id,
                project_item_id=project_item_id,
                status=operation.desired_status,
            )

            print("Status updated.")
            print()


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


def _get_created_epic(
        epic_id: str,
        created_epics: dict[str, dict],
) -> dict:
    if epic_id not in created_epics:
        raise RuntimeError(
            f"Cannot attach issue to epic because epic was not created in this execution: {epic_id}"
        )

    return created_epics[epic_id]


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