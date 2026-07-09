from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    CreateCommentOperation,
    CreateIssueOperation,
    plan_reconcile_backlog,
)
from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue, Project


def test_reconcile_plans_missing_issue_comment_for_existing_issue():
    backlog = _backlog_with_issue_comment()

    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=[
            _live_epic("source-epic"),
            _live_issue("existing-issue", comments=[]),
        ],
    )

    comment_operations = [
        operation
        for operation in plan.operations
        if isinstance(operation, CreateCommentOperation)
    ]

    assert len(comment_operations) == 1
    assert comment_operations[0].item.id == "existing-issue"
    assert comment_operations[0].comment.id == "comment-1"


def test_reconcile_does_not_duplicate_existing_provider_comment_and_hydrates_metadata():
    backlog = _backlog_with_issue_comment()
    comment = backlog.epics[0].issues[0].comments[0]

    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=[
            _live_epic("source-epic"),
            _live_issue(
                "existing-issue",
                comments=[
                    _live_comment(
                        comment_id="comment-1",
                        github_id="github-comment-id",
                        database_id=123,
                        url="https://github.com/ggortsema/source-repo/issues/2#issuecomment-123",
                    )
                ],
            ),
        ],
    )

    assert not any(
        isinstance(operation, CreateCommentOperation)
        for operation in plan.operations
    )

    assert comment.provider_metadata["github"] == {
        "comment_id": "github-comment-id",
        "database_id": 123,
        "url": "https://github.com/ggortsema/source-repo/issues/2#issuecomment-123",
        "created_at": "2026-07-09T12:00:00Z",
        "updated_at": "2026-07-09T12:00:00Z",
    }


def test_reconcile_plans_comment_after_creating_missing_issue():
    backlog = _backlog_with_issue_comment()

    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=[
            _live_epic("source-epic"),
        ],
    )

    operation_types = [
        type(operation)
        for operation in plan.operations
    ]

    assert CreateIssueOperation in operation_types
    assert CreateCommentOperation in operation_types

    create_issue_index = operation_types.index(CreateIssueOperation)
    create_comment_index = operation_types.index(CreateCommentOperation)

    assert create_issue_index < create_comment_index


def test_reconcile_plans_missing_epic_comment_for_existing_epic():
    backlog = _backlog_with_epic_comment()

    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=[
            _live_epic("source-epic", comments=[]),
        ],
    )

    comment_operations = [
        operation
        for operation in plan.operations
        if isinstance(operation, CreateCommentOperation)
    ]

    assert len(comment_operations) == 1
    assert comment_operations[0].item.id == "source-epic"
    assert comment_operations[0].comment.id == "epic-comment-1"


def _backlog_with_issue_comment() -> Backlog:
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            number=1,
            url="https://github.com/users/ggortsema/projects/1",
            provider_metadata={"github": {"project_id": "test-project-id"}},
        ),
        epics=[
            Epic(
                id="source-epic",
                type="epic",
                title="Source Epic",
                repository="ggortsema/source-repo",
                status="Backlog",
                issue_state="OPEN",
                order=1000,
                description="Source epic description.",
                acceptance_criteria=[],
                comments=[],
                labels=[],
                assignees=[],
                milestone="Source Milestone",
                provider_metadata={"github": {}},
                issues=[
                    Issue(
                        id="existing-issue",
                        type="issue",
                        title="Existing Issue",
                        repository="ggortsema/source-repo",
                        status="Ready",
                        issue_state="OPEN",
                        order=1000,
                        description="Existing issue description.",
                        acceptance_criteria=[],
                        comments=[
                            Comment(
                                id="comment-1",
                                body="This comment should be written to GitHub.",
                                source="johnny-johnny",
                                created_at="2026-07-09T12:00:00Z",
                                provider_metadata={"github": {}},
                            )
                        ],
                        labels=[],
                        assignees=[],
                        milestone="Source Milestone",
                        provider_metadata={"github": {}},
                    )
                ],
            )
        ],
    )


def _backlog_with_epic_comment() -> Backlog:
    backlog = _backlog_with_issue_comment()
    backlog.epics[0].comments = [
        Comment(
            id="epic-comment-1",
            body="This epic comment should be written to GitHub.",
            source="johnny-johnny",
            created_at="2026-07-09T12:00:00Z",
            provider_metadata={"github": {}},
        )
    ]
    backlog.epics[0].issues = []
    return backlog


def _live_epic(
        jj_id: str,
        comments: list[dict] | None = None,
) -> dict:
    return {
        "project_item_id": f"{jj_id}-project-item-id",
        "project_status": "Backlog",
        "id": f"{jj_id}-github-id",
        "database_id": 1,
        "number": 1,
        "title": "[Epic] Source Epic",
        "body": _metadata_block(
            jj_id=jj_id,
            item_type="epic",
        ),
        "url": f"https://github.com/ggortsema/source-repo/issues/1",
        "state": "OPEN",
        "created_at": "2026-07-09T12:00:00Z",
        "updated_at": "2026-07-09T12:00:00Z",
        "repository": "ggortsema/source-repo",
        "labels": [],
        "assignees": [],
        "milestone": "Source Milestone",
        "comments": comments or [],
    }


def _live_issue(
        jj_id: str,
        comments: list[dict] | None = None,
) -> dict:
    return {
        "project_item_id": f"{jj_id}-project-item-id",
        "project_status": "Ready",
        "id": f"{jj_id}-github-id",
        "database_id": 2,
        "number": 2,
        "title": "Existing Issue",
        "body": _metadata_block(
            jj_id=jj_id,
            item_type="issue",
            parent="source-epic",
        ),
        "url": f"https://github.com/ggortsema/source-repo/issues/2",
        "state": "OPEN",
        "created_at": "2026-07-09T12:00:00Z",
        "updated_at": "2026-07-09T12:00:00Z",
        "repository": "ggortsema/source-repo",
        "labels": [],
        "assignees": [],
        "milestone": "Source Milestone",
        "comments": comments or [],
    }


def _live_comment(
        comment_id: str,
        github_id: str,
        database_id: int,
        url: str,
) -> dict:
    return {
        "id": github_id,
        "database_id": database_id,
        "body": _metadata_block(
            jj_id=comment_id,
            item_type="comment",
            parent="existing-issue",
        ),
        "url": url,
        "created_at": "2026-07-09T12:00:00Z",
        "updated_at": "2026-07-09T12:00:00Z",
    }


def _metadata_block(
        jj_id: str,
        item_type: str,
        parent: str | None = None,
) -> str:
    lines = [
        "<!-- johnny-johnny",
        f"id: {jj_id}",
        "schema: backlog-v1",
        f"type: {item_type}",
    ]

    if parent is not None:
        lines.append(f"parent: {parent}")

    lines.append("-->")

    return "\n".join(lines)