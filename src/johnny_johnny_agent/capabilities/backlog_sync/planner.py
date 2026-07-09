from dataclasses import dataclass, field
from typing import Any, Union

from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue


BacklogItem = Epic | Issue


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
    issue: BacklogItem
    current_status: str | None
    desired_status: str


@dataclass
class CreateCommentOperation:
    item: BacklogItem
    comment: Comment


BacklogOperation = Union[
    CreateEpicOperation,
    CreateIssueOperation,
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    UpdateIssueStatusOperation,
    CreateCommentOperation,
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
            operations.append(
                UpdateIssueStatusOperation(
                    issue=epic,
                    current_status=None,
                    desired_status=epic.status,
                )
            )
            operations.extend(_comment_operations_for_item(epic, None))

        else:
            hydrated_epic = _item_with_live_github_metadata(epic, live_epic)
            current_epic_status = live_epic.get("project_status")

            if current_epic_status != epic.status:
                operations.append(
                    UpdateIssueStatusOperation(
                        issue=hydrated_epic,
                        current_status=current_epic_status,
                        desired_status=epic.status,
                    )
                )

            operations.extend(_comment_operations_for_item(hydrated_epic, live_epic))

        for issue in epic.issues:
            live_issue = live_by_jj_id.get(issue.id)

            if live_issue is None:
                operations.append(CreateIssueOperation(issue=issue, parent_epic=epic))
                operations.append(AddIssueToProjectOperation(issue=issue))
                operations.append(
                    UpdateIssueStatusOperation(
                        issue=issue,
                        current_status=None,
                        desired_status=issue.status,
                    )
                )
                operations.append(
                    AttachIssueToEpicOperation(
                        issue=issue,
                        parent_epic=epic,
                    )
                )
                operations.extend(_comment_operations_for_item(issue, None))
                continue

            hydrated_issue = _item_with_live_github_metadata(issue, live_issue)
            current_status = live_issue.get("project_status")

            if current_status != issue.status:
                operations.append(
                    UpdateIssueStatusOperation(
                        issue=hydrated_issue,
                        current_status=current_status,
                        desired_status=issue.status,
                    )
                )

            operations.extend(_comment_operations_for_item(hydrated_issue, live_issue))

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


def _comment_operations_for_item(
        item: BacklogItem,
        live_issue: dict[str, Any] | None,
) -> list[CreateCommentOperation]:
    operations: list[CreateCommentOperation] = []

    if live_issue is None:
        return [
            CreateCommentOperation(
                item=item,
                comment=comment,
            )
            for comment in item.comments
        ]

    live_comments = live_issue.get("comments")

    if live_comments is None:
        return [
            CreateCommentOperation(
                item=item,
                comment=comment,
            )
            for comment in item.comments
            if not _has_github_comment_metadata(comment)
        ]

    live_comments_by_jj_id = _index_live_comments_by_jj_id(live_comments)

    for comment in item.comments:
        live_comment = live_comments_by_jj_id.get(comment.id)

        if live_comment is not None:
            _hydrate_comment_github_metadata(comment, live_comment)
            continue

        operations.append(
            CreateCommentOperation(
                item=item,
                comment=comment,
            )
        )

    return operations


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


def _index_live_comments_by_jj_id(
        live_comments: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for live_comment in live_comments:
        metadata = _extract_johnny_metadata(live_comment.get("body", ""))

        if metadata.get("type") != "comment":
            continue

        jj_id = metadata.get("id")

        if jj_id:
            result[jj_id] = live_comment

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


def _item_with_live_github_metadata(
        item: BacklogItem,
        live_issue: dict[str, Any],
) -> BacklogItem:
    item.provider_metadata["github"] = {
        **item.provider_metadata.get("github", {}),
        "issue_id": live_issue.get("id") or live_issue.get("issue_id"),
        "database_id": live_issue.get("databaseId") or live_issue.get("database_id"),
        "number": live_issue.get("number"),
        "url": live_issue.get("url"),
        "project_item_id": live_issue.get("project_item_id"),
    }

    return item


def _hydrate_comment_github_metadata(
        comment: Comment,
        live_comment: dict[str, Any],
) -> None:
    current_github_metadata = comment.provider_metadata.get("github", {})

    github_metadata = {
        **current_github_metadata,
        "comment_id": live_comment.get("id") or live_comment.get("comment_id"),
        "database_id": live_comment.get("databaseId") or live_comment.get("database_id"),
        "url": live_comment.get("url"),
        "created_at": live_comment.get("createdAt") or live_comment.get("created_at"),
        "updated_at": live_comment.get("updatedAt") or live_comment.get("updated_at"),
    }

    comment.provider_metadata["github"] = {
        key: value
        for key, value in github_metadata.items()
        if value is not None
    }


def _has_github_comment_metadata(comment: Comment) -> bool:
    return bool(
        comment.provider_metadata
        .get("github", {})
        .get("comment_id")
    )