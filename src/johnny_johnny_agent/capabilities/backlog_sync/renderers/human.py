from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    find_epic_issues,
    find_parent_epic,
)
from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue


BacklogItem = Epic | Issue


def render_human_backlog_item(
        backlog: Backlog,
        item: BacklogItem,
) -> str:
    if isinstance(item, Epic):
        return _render_epic(backlog, item)

    if isinstance(item, Issue):
        return _render_issue(backlog, item)

    raise RuntimeError(f"Unsupported backlog item type: {type(item)}")


def render_human_backlog_items(items: list[BacklogItem | dict[str, str]]) -> str:
    if not items:
        return "No items found."

    lines = [
        f"{'STATUS':<14} {'ID':<40} TITLE",
        f"{'-' * 14} {'-' * 40} {'-' * 40}",
    ]

    for item in items:
        if isinstance(item, dict):
            status = item["status"]
            item_id = item["id"]
            title = item["title"]
        else:
            status = item.status
            item_id = item.id
            title = item.title

        lines.append(
            f"{status:<14} "
            f"{item_id:<40} "
            f"{title}"
        )

    return "\n".join(lines)


def _render_epic(
        backlog: Backlog,
        epic: Epic,
) -> str:
    child_issues = find_epic_issues(
        backlog=backlog,
        epic_id=epic.id,
    )

    lines = [
        "Epic",
        "----",
        "",
        "Title:",
        epic.title,
        "",
        "ID:",
        epic.id,
        "",
        "Status:",
        epic.status,
        "",
        "Repository:",
        epic.repository,
        "",
        "Description:",
        epic.description or "(none)",
        "",
        "Acceptance Criteria:",
        *_render_list(epic.acceptance_criteria),
        "",
        "Child Issues:",
        render_human_backlog_items(child_issues),
        "",
        "Comments:",
        *_render_comments(epic.comments),
        ]

    return "\n".join(lines)


def _render_issue(
        backlog: Backlog,
        issue: Issue,
) -> str:
    parent_epic = find_parent_epic(
        backlog=backlog,
        issue_id=issue.id,
    )

    lines = [
        "Issue",
        "-----",
        "",
        "Title:",
        issue.title,
        "",
        "ID:",
        issue.id,
        "",
        "Status:",
        issue.status,
        "",
        "Repository:",
        issue.repository,
        "",
        "Parent Epic:",
        f"{parent_epic.title} [{parent_epic.id}]",
        "",
        "Description:",
        issue.description or "(none)",
        "",
        "Acceptance Criteria:",
        *_render_list(issue.acceptance_criteria),
        "",
        "Comments:",
        *_render_comments(issue.comments),
        ]

    return "\n".join(lines)


def _render_list(items: list[str]) -> list[str]:
    if not items:
        return ["- (none)"]

    return [
        f"- {item}"
        for item in items
    ]


def _render_comments(comments: list[Comment]) -> list[str]:
    if not comments:
        return ["- (none)"]

    lines = []

    for comment in comments:
        created_at = comment.created_at or "unknown-time"
        source = comment.source or "unknown-source"

        lines.append(f"- {created_at} {source}")

        for body_line in comment.body.splitlines() or [""]:
            lines.append(f"  {body_line}")

    return lines