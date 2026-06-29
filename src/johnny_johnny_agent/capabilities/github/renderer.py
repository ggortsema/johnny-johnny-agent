from johnny_johnny_agent.capabilities.github.metadata import (
    JohnnyMetadata,
    render_johnny_metadata,
)
from johnny_johnny_agent.domain.backlog import Epic, Issue


BACKLOG_SCHEMA = "backlog-v1"


def render_epic_body(epic: Epic) -> str:
    metadata = JohnnyMetadata(
        id=epic.id,
        schema=BACKLOG_SCHEMA,
        type="epic",
    )

    return _render_body(
        metadata=metadata,
        description=epic.description,
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
    )


def _render_body(metadata: JohnnyMetadata, description: str) -> str:
    body_parts = [
        render_johnny_metadata(metadata),
    ]

    if description:
        body_parts.extend(["", description])

    return "\n".join(body_parts)