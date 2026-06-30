from dataclasses import dataclass, field
from typing import Any, Union

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


@dataclass
class DeleteIssueOperation:
    issue: Issue


@dataclass
class CreateEpicOperation:
    epic: Epic


@dataclass
class CreateIssueOperation:
    issue: Issue
    parent_epic: Epic


@dataclass
class AddIssueToProjectOperation:
    issue: Issue


@dataclass
class AttachIssueToEpicOperation:
    issue: Issue
    parent_epic: Epic


@dataclass
class UpdateIssueStatusOperation:
    issue: Issue
    current_status: str | None
    desired_status: str


BacklogOperation = Union[
    CreateEpicOperation,
    CreateIssueOperation,
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    UpdateIssueStatusOperation,
    DeleteIssueOperation,
]


@dataclass
class ExecutionPlan:
    operations: list[BacklogOperation] = field(default_factory=list)


def plan_reconcile_backlog(
        backlog: Backlog,
        current_project_issues: list[dict[str, Any]],
) -> ExecutionPlan:
    operations: list[BacklogOperation] = []

    live_by_jj_id = _index_live_items_by_jj_id(current_project_issues)
    canonical_issue_ids = _canonical_issue_ids(backlog)

    for epic in backlog.epics:
        live_epic = live_by_jj_id.get(epic.id)

        if live_epic is None:
            operations.append(CreateEpicOperation(epic=epic))

        for issue in epic.issues:
            live_issue = live_by_jj_id.get(issue.id)

            if live_issue is None:
                operations.append(CreateIssueOperation(issue=issue, parent_epic=epic))
                operations.append(AddIssueToProjectOperation(issue=issue))
                operations.append(
                    AttachIssueToEpicOperation(
                        issue=issue,
                        parent_epic=epic,
                    )
                )
                continue

            current_status = live_issue.get("project_status")

            if current_status != issue.status:
                operations.append(
                    UpdateIssueStatusOperation(
                        issue=_issue_with_live_github_metadata(issue, live_issue),
                        current_status=current_status,
                        desired_status=issue.status,
            )
    )

    for jj_id, live_issue in live_by_jj_id.items():
        if not _is_live_johnny_issue(live_issue):
            continue

        if jj_id in canonical_issue_ids:
            continue

        operations.append(
            DeleteIssueOperation(
                issue=_live_issue_to_model(jj_id, live_issue),
            )
        )

    return ExecutionPlan(operations=operations)


def _canonical_issue_ids(backlog: Backlog) -> set[str]:
    return {
        issue.id
        for epic in backlog.epics
        for issue in epic.issues
    }


def _is_live_johnny_issue(live_issue: dict[str, Any]) -> bool:
    metadata = _extract_johnny_metadata(live_issue.get("body", ""))
    return metadata.get("type") == "issue"


def _live_issue_to_model(
        jj_id: str,
        live_issue: dict[str, Any],
) -> Issue:
    return Issue(
        id=jj_id,
        type="issue",
        title=live_issue.get("title", jj_id),
        repository=live_issue.get("repository", ""),
        status=live_issue.get("project_status") or "Backlog",
        issue_state=live_issue.get("state") or "OPEN",
        order=0,
        description=live_issue.get("body", ""),
        acceptance_criteria=[],
        labels=[],
        assignees=[],
        milestone=None,
        provider_metadata={
            "github": {
                "issue_id": live_issue.get("id") or live_issue.get("issue_id"),
                "database_id": live_issue.get("databaseId") or live_issue.get("database_id"),
                "number": live_issue.get("number"),
                "url": live_issue.get("url"),
                "project_item_id": live_issue.get("project_item_id"),
            }
        },
    )


def _index_live_items_by_jj_id(
        current_project_issues: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for row in current_project_issues:
        metadata = _extract_johnny_metadata(row.get("body", ""))

        jj_id = metadata.get("id")

        if jj_id:
            result[jj_id] = row

    return result


def _extract_johnny_metadata(body: str) -> dict[str, str]:
    start = body.find("<!-- johnny-johnny")

    if start == -1:
        return {}

    end = body.find("-->", start)

    if end == -1:
        return {}

    block = body[start:end]

    result: dict[str, str] = {}

    for line in block.splitlines():
        line = line.strip()

        if not line or line.startswith("<!--"):
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()

    return result

def _issue_with_live_github_metadata(
        issue: Issue,
        live_issue: dict[str, Any],
) -> Issue:
    issue.provider_metadata["github"] = {
        **issue.provider_metadata.get("github", {}),
        "issue_id": live_issue.get("id") or live_issue.get("issue_id"),
        "database_id": live_issue.get("databaseId") or live_issue.get("database_id"),
        "number": live_issue.get("number"),
        "url": live_issue.get("url"),
        "project_item_id": live_issue.get("project_item_id"),
    }

    return issue