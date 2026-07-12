from __future__ import annotations

import hashlib

import pytest

from johnny_johnny_agent.capabilities.backlog_retrieval.documents import (
    BacklogRetrievalDocument,
    build_backlog_retrieval_document,
)
from johnny_johnny_agent.domain.backlog import Comment, Epic, Issue


def _epic(
        *,
        title: str = "  Backlog-as-Code Synchronization  ",
        status: str = "In Progress",
) -> Epic:
    return Epic(
        id="backlog-as-code-synchronization",
        type="epic",
        title=title,
        repository="ggortsema/johnny-johnny-agent",
        status=status,
        issue_state="open",
        order=1,
        description="  Synchronize canonical backlog state with providers.  ",
        acceptance_criteria=[
            "  Canonical IDs remain stable.  ",
            "",
            "Provider failures are reported explicitly.",
        ],
        comments=[
            Comment(
                id="comment-1",
                body="This comment should not be embedded.",
            )
        ],
        labels=["architecture"],
        assignees=["ggortsema"],
        provider_metadata={"github": {"issue_number": 100}},
    )


def _issue(
        *,
        status: str = "Ready",
) -> Issue:
    return Issue(
        id="implement-github-webhook-synchronization",
        type="issue",
        title="  Implement GitHub Webhook Synchronization  ",
        repository="ggortsema/johnny-johnny-agent",
        status=status,
        issue_state="open",
        order=2,
        description=(
            "  Receive and validate GitHub webhook events and synchronize "
            "provider-originated changes.  "
        ),
        acceptance_criteria=[
            "Validate webhook signatures.",
            "  Avoid synchronization loops.  ",
        ],
        comments=[
            Comment(
                id="comment-2",
                body="Starting the implementation.",
            )
        ],
        labels=["github"],
        assignees=["ggortsema"],
        provider_metadata={"github": {"issue_number": 101}},
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_builds_epic_retrieval_document_from_stable_descriptive_fields():
    source_text = (
        "Type: Epic\n"
        "Title: Backlog-as-Code Synchronization\n"
        "Canonical ID: backlog-as-code-synchronization\n"
        "\n"
        "Description:\n"
        "Synchronize canonical backlog state with providers.\n"
        "\n"
        "Acceptance criteria:\n"
        "- Canonical IDs remain stable.\n"
        "- Provider failures are reported explicitly."
    )

    document = build_backlog_retrieval_document(_epic())

    assert document == BacklogRetrievalDocument(
        canonical_id="backlog-as-code-synchronization",
        item_type="epic",
        source_text=source_text,
        source_hash=_sha256(source_text),
    )


def test_builds_issue_retrieval_document_with_parent_epic_context():
    source_text = (
        "Type: Issue\n"
        "Title: Implement GitHub Webhook Synchronization\n"
        "Canonical ID: implement-github-webhook-synchronization\n"
        "Epic: Backlog-as-Code Synchronization\n"
        "Epic canonical ID: backlog-as-code-synchronization\n"
        "\n"
        "Description:\n"
        "Receive and validate GitHub webhook events and synchronize "
        "provider-originated changes.\n"
        "\n"
        "Acceptance criteria:\n"
        "- Validate webhook signatures.\n"
        "- Avoid synchronization loops."
    )

    document = build_backlog_retrieval_document(
        _issue(),
        parent_epic=_epic(),
    )

    assert document == BacklogRetrievalDocument(
        canonical_id="implement-github-webhook-synchronization",
        item_type="issue",
        source_text=source_text,
        source_hash=_sha256(source_text),
    )


def test_operational_status_change_does_not_change_document_or_hash():
    ready_document = build_backlog_retrieval_document(
        _issue(status="Ready"),
        parent_epic=_epic(),
    )
    in_progress_document = build_backlog_retrieval_document(
        _issue(status="In Progress"),
        parent_epic=_epic(),
    )

    assert ready_document == in_progress_document


def test_parent_epic_title_change_changes_issue_document_hash():
    original_document = build_backlog_retrieval_document(
        _issue(),
        parent_epic=_epic(),
    )
    renamed_document = build_backlog_retrieval_document(
        _issue(),
        parent_epic=_epic(title="Provider Synchronization"),
    )

    assert original_document.source_text != renamed_document.source_text
    assert original_document.source_hash != renamed_document.source_hash


def test_retrieval_document_excludes_operational_and_provider_state():
    document = build_backlog_retrieval_document(
        _issue(),
        parent_epic=_epic(),
    )

    assert "Ready" not in document.source_text
    assert "Starting the implementation" not in document.source_text
    assert "ggortsema" not in document.source_text
    assert "101" not in document.source_text


def test_issue_requires_parent_epic():
    with pytest.raises(
            ValueError,
            match="A parent epic is required",
    ):
        build_backlog_retrieval_document(_issue())