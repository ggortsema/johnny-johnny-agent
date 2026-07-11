"""Conversion helpers from domain/application objects to REST contracts."""

from __future__ import annotations

from johnny_johnny_agent.api.models import (
    BacklogItemResponse,
    BacklogItemSummaryResponse,
    CommentResponse,
    ProjectResponse,
    PurgeIssueResponse,
    ReconcileOperationResponse,
)
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    BacklogOperation,
    CreateCommentOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    DeleteIssueOperation,
    UpdateIssueStatusOperation,
)
from johnny_johnny_agent.domain.backlog import Comment, Epic, Issue, Project


def project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        provider=project.provider,
        title=project.title,
        number=project.number,
        url=project.url,
        provider_metadata=project.provider_metadata,
    )


def comment_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        body=comment.body,
        source=comment.source,
        created_at=comment.created_at,
        provider_metadata=comment.provider_metadata,
    )


def item_summary_response(
    item: Epic | Issue,
    *,
    parent_epic_id: str | None = None,
) -> BacklogItemSummaryResponse:
    return BacklogItemSummaryResponse(
        id=item.id,
        type=item.type,
        title=item.title,
        repository=item.repository,
        status=item.status,
        issue_state=item.issue_state,
        order=item.order,
        parent_epic_id=parent_epic_id,
        issue_count=len(item.issues) if isinstance(item, Epic) else None,
    )


def item_response(
    item: Epic | Issue,
    *,
    parent_epic_id: str | None = None,
    include_children: bool = True,
) -> BacklogItemResponse:
    issues = []
    if isinstance(item, Epic) and include_children:
        issues = [
            item_response(issue, parent_epic_id=item.id)
            for issue in sorted(item.issues, key=lambda child: child.order)
        ]

    return BacklogItemResponse(
        id=item.id,
        type=item.type,
        title=item.title,
        repository=item.repository,
        status=item.status,
        issue_state=item.issue_state,
        order=item.order,
        description=item.description,
        acceptance_criteria=list(item.acceptance_criteria),
        comments=[comment_response(comment) for comment in item.comments],
        labels=list(item.labels),
        assignees=list(item.assignees),
        milestone=item.milestone,
        provider_metadata=item.provider_metadata,
        parent_epic_id=parent_epic_id,
        issues=issues,
    )


def reconcile_operation_response(
    operation: BacklogOperation,
) -> ReconcileOperationResponse:
    if isinstance(operation, CreateEpicOperation):
        return _operation("create_epic", operation.epic)
    if isinstance(operation, CreateIssueOperation):
        return _operation(
            "create_issue",
            operation.issue,
            parent_epic_id=operation.parent_epic.id,
        )
    if isinstance(operation, AddIssueToProjectOperation):
        return _operation("add_issue_to_project", operation.issue)
    if isinstance(operation, AttachIssueToEpicOperation):
        return _operation(
            "attach_issue_to_epic",
            operation.issue,
            parent_epic_id=operation.parent_epic.id,
        )
    if isinstance(operation, UpdateIssueStatusOperation):
        return _operation(
            "update_issue_status",
            operation.issue,
            current_status=operation.current_status,
            desired_status=operation.desired_status,
        )
    if isinstance(operation, CreateCommentOperation):
        return _operation(
            "create_comment",
            operation.item,
            comment_id=operation.comment.id,
        )
    if isinstance(operation, DeleteIssueOperation):
        return _operation("delete_issue", operation.issue)
    raise TypeError(f"Unsupported reconciliation operation: {type(operation).__name__}")


def purge_issue_response(issue: dict) -> PurgeIssueResponse:
    return PurgeIssueResponse(
        id=_optional_string(issue.get("id") or issue.get("issue_id")),
        number=issue.get("number"),
        title=issue.get("title"),
        url=issue.get("url"),
    )


def _operation(
    kind: str,
    item: Epic | Issue,
    *,
    parent_epic_id: str | None = None,
    comment_id: str | None = None,
    current_status: str | None = None,
    desired_status: str | None = None,
) -> ReconcileOperationResponse:
    return ReconcileOperationResponse(
        kind=kind,
        item_id=item.id,
        title=item.title,
        parent_epic_id=parent_epic_id,
        comment_id=comment_id,
        current_status=current_status,
        desired_status=desired_status,
    )


def _optional_string(value: object | None) -> str | None:
    return None if value is None else str(value)
