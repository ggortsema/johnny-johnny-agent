import re
from datetime import datetime, timezone
from uuid import uuid4

from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue


BacklogItem = Epic | Issue


def create_issue(
        backlog: Backlog,
        title: str,
        epic_id: str,
        *,
        issue_id: str | None = None,
        description: str = "",
        repository: str | None = None,
        acceptance_criteria: list[str] | None = None,
) -> Issue:
    epic = find_epic(backlog, epic_id)
    resolved_issue_id = issue_id or _slugify(title)

    _ensure_item_id_is_unique(backlog, resolved_issue_id)

    issue = Issue(
        id=resolved_issue_id,
        type="issue",
        title=title,
        repository=repository or epic.repository,
        status="Backlog",
        issue_state="OPEN",
        order=_next_issue_order(epic),
        description=description,
        acceptance_criteria=acceptance_criteria or [],
        labels=[],
        assignees=[],
        milestone=epic.milestone,
        provider_metadata={"github": {}},
    )

    epic.issues.append(issue)

    return issue


def update_issue(
        backlog: Backlog,
        issue_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        acceptance_criteria: list[str] | None = None,
        comment: str | None = None,
) -> BacklogItem:
    item = find_backlog_item(backlog, issue_id)

    if title is not None:
        item.title = title

    if description is not None:
        item.description = description

    if status is not None:
        item.status = _normalize_status(status)

    if acceptance_criteria is not None:
        item.acceptance_criteria = acceptance_criteria

    if comment is not None:
        item.comments.append(
            Comment(
                id=f"comment-{uuid4().hex}",
                body=comment,
                source="johnny-johnny",
                created_at=datetime.now(timezone.utc).isoformat(),
                provider_metadata={"github": {}},
            )
        )

    return item


def update_issue_status(
        backlog: Backlog,
        issue_id: str,
        status: str,
) -> BacklogItem:
    return update_issue(
        backlog=backlog,
        issue_id=issue_id,
        status=status,
    )


def find_backlog_item(
        backlog: Backlog,
        item_id: str,
) -> BacklogItem:
    for epic in backlog.epics:
        if epic.id == item_id:
            return epic

        for issue in epic.issues:
            if issue.id == item_id:
                return issue

    raise RuntimeError(f"Backlog item not found: {item_id}")


def find_issue(
        backlog: Backlog,
        issue_id: str,
) -> Issue:
    item = find_backlog_item(backlog, issue_id)

    if not isinstance(item, Issue):
        raise RuntimeError(f"Issue not found: {issue_id}")

    return item


def find_epic(
        backlog: Backlog,
        epic_id: str,
) -> Epic:
    for epic in backlog.epics:
        if epic.id == epic_id:
            return epic

    raise RuntimeError(f"Epic not found: {epic_id}")

def find_parent_epic(
        backlog: Backlog,
        issue_id: str,
) -> Epic:
    for epic in backlog.epics:
        for issue in epic.issues:
            if issue.id == issue_id:
                return epic

    raise RuntimeError(f"Parent epic not found for issue: {issue_id}")

def find_epic_issues(
        backlog: Backlog,
        epic_id: str,
        *,
        statuses: list[str] | None = None,
        excluded_statuses: list[str] | None = None,
) -> list[Issue]:
    epic = find_epic(backlog, epic_id)
    issues = epic.issues

    if statuses:
        normalized_statuses = {
            _normalize_status(status)
            for status in statuses
        }

        issues = [
            issue
            for issue in issues
            if issue.status in normalized_statuses
        ]

    elif excluded_statuses:
        normalized_excluded_statuses = {
            _normalize_status(status)
            for status in excluded_statuses
        }

        issues = [
            issue
            for issue in issues
            if issue.status not in normalized_excluded_statuses
        ]

    return sorted(
        issues,
        key=lambda issue: (
            _status_sort_order(issue.status),
            issue.order,
            issue.title.lower(),
        ),
    )


def delete_issue(
        backlog: Backlog,
        issue_id: str,
) -> Issue:
    for epic in backlog.epics:
        for index, issue in enumerate(epic.issues):
            if issue.id == issue_id:
                del epic.issues[index]
                return issue

    raise RuntimeError(f"Issue not found: {issue_id}")


def create_epic(
        backlog: Backlog,
        title: str,
        *,
        epic_id: str | None = None,
        description: str = "",
        repository: str,
        acceptance_criteria: list[str] | None = None,
) -> Epic:
    resolved_epic_id = epic_id or _slugify(title)

    _ensure_item_id_is_unique(backlog, resolved_epic_id)

    epic = Epic(
        id=resolved_epic_id,
        type="epic",
        title=title,
        repository=repository,
        status="Backlog",
        issue_state="OPEN",
        order=_next_epic_order(backlog),
        description=description,
        acceptance_criteria=acceptance_criteria or [],
        labels=[],
        assignees=[],
        milestone=None,
        provider_metadata={"github": {}},
        issues=[],
    )

    backlog.epics.append(epic)

    return epic


def _next_issue_order(epic: Epic) -> int:
    if not epic.issues:
        return 1000

    return max(issue.order for issue in epic.issues) + 1000


def _next_epic_order(backlog: Backlog) -> int:
    if not backlog.epics:
        return 1000

    return max(epic.order for epic in backlog.epics) + 1000


def _ensure_item_id_is_unique(
        backlog: Backlog,
        item_id: str,
) -> None:
    for epic in backlog.epics:
        if epic.id == item_id:
            raise RuntimeError(f"Backlog item already exists: {item_id}")

        for issue in epic.issues:
            if issue.id == item_id:
                raise RuntimeError(f"Backlog item already exists: {item_id}")


def _normalize_status(status: str) -> str:
    normalized = status.strip()

    status_by_lowercase = {
        "backlog": "Backlog",
        "ready": "Ready",
        "in progress": "In Progress",
        "in review": "In Review",
        "done": "Done",
    }

    return status_by_lowercase.get(normalized.lower(), normalized)


def _status_sort_order(status: str) -> int:
    status_order = {
        "Backlog": 0,
        "Ready": 1,
        "In Progress": 2,
        "In Review": 3,
        "Done": 4,
    }

    return status_order.get(status, 999)


def _slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        raise RuntimeError("Cannot generate issue id from an empty title.")

    return slug