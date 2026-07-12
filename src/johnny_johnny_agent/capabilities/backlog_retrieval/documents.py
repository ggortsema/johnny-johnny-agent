"""Build deterministic text documents for semantic backlog retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from johnny_johnny_agent.domain.backlog import Epic, Issue


@dataclass(frozen=True)
class BacklogRetrievalDocument:
    """One canonical backlog item represented for semantic retrieval."""

    canonical_id: str
    item_type: str
    source_text: str
    source_hash: str


def build_backlog_retrieval_document(
        item: Epic | Issue,
        *,
        parent_epic: Epic | None = None,
) -> BacklogRetrievalDocument:
    """Build stable descriptive text without operational or provider state."""

    if isinstance(item, Epic):
        if parent_epic is not None:
            raise ValueError("An epic retrieval document cannot have a parent epic.")

        lines = [
            "Type: Epic",
            f"Title: {item.title.strip()}",
            f"Canonical ID: {item.id}",
        ]

    elif isinstance(item, Issue):
        if parent_epic is None:
            raise ValueError(
                "A parent epic is required for an issue retrieval document."
            )

        lines = [
            "Type: Issue",
            f"Title: {item.title.strip()}",
            f"Canonical ID: {item.id}",
            f"Epic: {parent_epic.title.strip()}",
            f"Epic canonical ID: {parent_epic.id}",
        ]

    else:
        raise TypeError(
            "Backlog retrieval documents can only be built from Epic or Issue."
        )

    description = item.description.strip()
    if description:
        lines.extend(
            [
                "",
                "Description:",
                description,
            ]
        )

    acceptance_criteria = [
        criterion.strip()
        for criterion in item.acceptance_criteria
        if criterion.strip()
    ]
    if acceptance_criteria:
        lines.extend(
            [
                "",
                "Acceptance criteria:",
                *[f"- {criterion}" for criterion in acceptance_criteria],
            ]
        )

    source_text = "\n".join(lines)

    return BacklogRetrievalDocument(
        canonical_id=item.id,
        item_type=item.type,
        source_text=source_text,
        source_hash=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    )