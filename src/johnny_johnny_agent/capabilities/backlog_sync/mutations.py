import re

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


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


def update_issue_status(
        backlog: Backlog,
        issue_id: str,
        status: str,
) -> Issue:
    issue = find_issue(backlog, issue_id)
    issue.status = status
    return issue


def find_issue(
        backlog: Backlog,
        issue_id: str,
) -> Issue:
    for epic in backlog.epics:
        for issue in epic.issues:
            if issue.id == issue_id:
                return issue

    raise RuntimeError(f"Issue not found: {issue_id}")


def find_epic(
        backlog: Backlog,
        epic_id: str,
) -> Epic:
    for epic in backlog.epics:
        if epic.id == epic_id:
            return epic

    raise RuntimeError(f"Epic not found: {epic_id}")



def _next_issue_order(epic: Epic) -> int:
    if not epic.issues:
        return 1000

    return max(issue.order for issue in epic.issues) + 1000


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


def _slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        raise RuntimeError("Cannot generate issue id from an empty title.")

    return slug

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

def _next_epic_order(backlog: Backlog) -> int:
    if not backlog.epics:
        return 1000

    return max(epic.order for epic in backlog.epics) + 1000