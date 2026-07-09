from johnny_johnny_agent.capabilities.github.metadata import (
    JohnnyMetadata,
    render_johnny_metadata,
)
from johnny_johnny_agent.domain.backlog import Comment, Epic, Issue


BACKLOG_SCHEMA = "backlog-v1"

BacklogItem = Epic | Issue


def render_epic_body(epic: Epic) -> str:
    metadata = JohnnyMetadata(
        id=epic.id,
        schema=BACKLOG_SCHEMA,
        type="epic",
    )

    return _render_body(
        metadata=metadata,
        description=epic.description,
        acceptance_criteria=epic.acceptance_criteria,
    )


def render_issue_body(issue: Issue, parent_epic: Epic) -> str:
    metadata = JohnnyMetadata(
        id=issue.id,
        schema=BACKLOG_SCHEMA,
        type="issue",
        parent=parent_epic.id,
    )

    return _render_body(
        metadata=metadata,
        description=issue.description,
        acceptance_criteria=issue.acceptance_criteria,
    )


def render_comment_body(
        item: BacklogItem,
        comment: Comment,
) -> str:
    metadata = JohnnyMetadata(
        id=comment.id,
        schema=BACKLOG_SCHEMA,
        type="comment",
        parent=item.id,
    )

    return _render_body(
        metadata=metadata,
        description=comment.body,
        acceptance_criteria=[],
    )


def _render_body(
        metadata: JohnnyMetadata,
        description: str,
        acceptance_criteria: list[str],
) -> str:
    body_parts = [
        render_johnny_metadata(metadata),
    ]

    if description:
        body_parts.extend(["", description])

    if acceptance_criteria:
        body_parts.extend(["", "## Acceptance Criteria", ""])

        for criterion in acceptance_criteria:
            body_parts.append(f"- [ ] {criterion}")

    return "\n".join(body_parts)