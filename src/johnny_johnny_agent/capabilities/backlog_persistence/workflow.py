"""Application workflows for PostgreSQL canonical backlog persistence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogImportResult,
    BacklogLocation,
    BacklogPersistenceError,
    DatabaseStatus,
    PostgresBacklogRepository,
)
from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    create_epic,
    create_issue as create_canonical_issue,
    delete_issue as delete_canonical_issue,
    find_backlog_item,
    find_epic,
    find_parent_epic,
    move_issue as move_canonical_issue,
    update_issue as update_canonical_item,
)
from johnny_johnny_agent.capabilities.backlog_sync.executor import (
    execute_reconciliation_plan,
)
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    AddIssueToProjectOperation,
    AttachIssueToEpicOperation,
    BacklogOperation,
    CreateCommentOperation,
    CreateEpicOperation,
    CreateIssueOperation,
    DeleteIssueOperation,
    ExecutionPlan,
    UpdateIssueStatusOperation,
    plan_reconcile_backlog,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_loader import (
    load_backlog_yaml,
    load_backlog_yaml_text,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_writer import render_backlog_yaml
from johnny_johnny_agent.capabilities.github.client import (
    add_issue_to_project,
    add_sub_issue,
    create_issue as create_github_issue,
    create_issue_comment,
    clear_project_item_status,
    delete_issue as delete_github_issue,
    delete_issue_comment as delete_github_issue_comment,
    delete_project_item as delete_github_project_item,
    get_issue as get_github_issue,
    get_issue_parent as get_github_issue_parent,
    get_repository,
    list_project_issues,
    remove_sub_issue,
    update_issue as update_github_issue,
    update_project_item_status,
)
from johnny_johnny_agent.capabilities.github.renderer import (
    render_comment_body,
    render_epic_body,
    render_issue_body,
)
from johnny_johnny_agent.config import resolve_database_url
from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


@dataclass(frozen=True)
class BacklogSummary:
    epic_count: int
    issue_count: int
    acceptance_criterion_count: int
    comment_count: int
    label_count: int
    assignee_count: int


@dataclass(frozen=True)
class BacklogExportResult:
    location: BacklogLocation
    output_path: str
    epic_count: int
    issue_count: int
    comment_count: int


@dataclass(frozen=True)
class BacklogYamlExportResult:
    location: BacklogLocation
    content: str
    epic_count: int
    issue_count: int
    comment_count: int


@dataclass(frozen=True)
class BacklogDeleteResult:
    issue: Issue
    parent_epic: Epic
    github_issue_deleted: bool


@dataclass(frozen=True)
class BacklogReconcilePreview:
    plan: ExecutionPlan
    execution_plan: ExecutionPlan
    total_operation_count: int
    execution_operation_count: int
    remaining_operation_count: int


@dataclass(frozen=True)
class BacklogReconcileResult:
    preview: BacklogReconcilePreview
    executed_group_count: int
    hydrated_item_count: int


@dataclass(frozen=True)
class BacklogPurgeResult:
    project_title: str
    issues: tuple[dict[str, Any], ...]
    total_issue_count: int
    deleted_issue_count: int
    remaining_issue_count: int
    cleared_item_count: int
    projection_metadata_cleared: bool


@dataclass(frozen=True)
class _GitHubEpicProjection:
    issue: dict[str, Any]
    project_item: dict[str, Any]
    project_id: str
    created_issue: bool
    created_project_item: bool


@dataclass
class _GitHubMutationState:
    issue: dict[str, Any] | None = None
    project_id: str | None = None
    project_item_id: str | None = None
    created_issue: bool = False
    created_project_item: bool = False
    prior_title: str | None = None
    prior_body: str | None = None
    prior_status: str | None = None
    prior_parent: dict[str, Any] | None = None
    target_parent: dict[str, Any] | None = None
    content_changed: bool = False
    status_changed: bool = False
    parent_changed: bool = False
    created_comment_id: str | None = None


class TargetedBacklogMutationCompensationError(RuntimeError):
    """Raised when provider compensation cannot fully restore consistency."""


class TargetedBacklogMutationConsistencyError(RuntimeError):
    """Raised when an irreversible provider mutation outlives DB rollback."""


def summarize_backlog(backlog: Backlog) -> BacklogSummary:
    items = [
        item
        for epic in backlog.epics
        for item in (epic, *epic.issues)
    ]
    return BacklogSummary(
        epic_count=len(backlog.epics),
        issue_count=sum(len(epic.issues) for epic in backlog.epics),
        acceptance_criterion_count=sum(
            len(item.acceptance_criteria) for item in items
        ),
        comment_count=sum(len(item.comments) for item in items),
        label_count=sum(len(set(item.labels)) for item in items),
        assignee_count=sum(len(set(item.assignees)) for item in items),
    )


def check_postgres_backlog_database(
    *,
    database_url: str | None = None,
) -> DatabaseStatus:
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    return repository.check()


def load_backlog_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    database_url: str | None = None,
) -> Backlog:
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    return repository.load(location)


def preview_create_epic_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    title: str,
    repository_name: str,
    epic_id: str | None = None,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
    database_url: str | None = None,
) -> Epic:
    """Build a new epic from the persisted backlog without writing it."""
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    return _build_epic(
        backlog=backlog,
        title=title,
        repository_name=repository_name,
        epic_id=epic_id,
        description=description,
        acceptance_criteria=acceptance_criteria,
    )


def create_epic_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    title: str,
    repository_name: str,
    epic_id: str | None = None,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
    database_url: str | None = None,
) -> Epic:
    """Create or safely repair one canonical epic and GitHub projection.

    A new epic remains uncommitted in PostgreSQL until its targeted GitHub
    projection and provider metadata are complete. Repeating the same create
    request is idempotent: if the canonical epic already exists with identical
    canonical content, the workflow repairs or confirms its projection instead
    of inserting a duplicate. Conflicting canonical content still fails.
    """
    if provider != "github":
        raise RuntimeError(
            "Targeted epic creation currently supports provider: github"
        )

    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    projection: _GitHubEpicProjection | None = None

    try:
        with repository.transaction() as transaction:
            backlog = transaction.load_backlog(
                location,
                lock_project=True,
            )
            resolved_epic_id = epic_id or _slugify_backlog_item_id(title)
            existing_epic = _find_epic_by_id(backlog, resolved_epic_id)

            if existing_epic is None:
                epic = _build_epic(
                    backlog=backlog,
                    title=title,
                    repository_name=repository_name,
                    epic_id=resolved_epic_id,
                    description=description,
                    acceptance_criteria=acceptance_criteria,
                )
                transaction.insert_epic(location, epic)
            else:
                epic = existing_epic
                _assert_matching_create_request(
                    epic=epic,
                    title=title,
                    repository_name=repository_name,
                    description=description,
                    acceptance_criteria=acceptance_criteria or [],
                )

            projection = _project_epic_to_github(backlog, epic)
            _hydrate_github_epic_metadata(epic, projection)
            transaction.update_epic_provider_metadata(location, epic)

        return epic
    except Exception as exc:
        if projection is not None:
            _compensate_github_projection(
                projection=projection,
                original_error=exc,
            )
        if isinstance(exc, RuntimeError):
            raise
        raise BacklogPersistenceError(
            f"PostgreSQL backlog persistence failed: {exc}"
        ) from exc


def _build_epic(
    *,
    backlog: Backlog,
    title: str,
    repository_name: str,
    epic_id: str | None,
    description: str,
    acceptance_criteria: list[str] | None,
) -> Epic:
    return create_epic(
        backlog=backlog,
        title=title,
        epic_id=epic_id,
        description=description,
        repository=repository_name,
        acceptance_criteria=acceptance_criteria or [],
    )



def _find_epic_by_id(backlog: Backlog, epic_id: str) -> Epic | None:
    for epic in backlog.epics:
        if epic.id == epic_id:
            return epic
    return None


def _assert_matching_create_request(
    *,
    epic: Epic,
    title: str,
    repository_name: str,
    description: str,
    acceptance_criteria: list[str],
) -> None:
    differences: list[str] = []
    if epic.title != title:
        differences.append("title")
    if epic.repository != repository_name:
        differences.append("repository")
    if epic.description != description:
        differences.append("description")
    if epic.acceptance_criteria != acceptance_criteria:
        differences.append("acceptance criteria")

    if differences:
        raise RuntimeError(
            f"Backlog item already exists with different {', '.join(differences)}: "
            f"{epic.id}"
        )


def _slugify_backlog_item_id(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        raise RuntimeError("Cannot generate issue id from an empty title.")
    return slug

def _project_epic_to_github(
    backlog: Backlog,
    epic: Epic,
) -> _GitHubEpicProjection:
    project_id = _github_project_id(backlog)
    existing = _find_existing_github_epic(project_id, epic.id)

    if existing is not None:
        project_item = {"id": existing["project_item_id"]}
        update_project_item_status(
            project_id=project_id,
            project_item_id=project_item["id"],
            status=epic.status,
        )
        return _GitHubEpicProjection(
            issue=existing,
            project_item=project_item,
            project_id=project_id,
            created_issue=False,
            created_project_item=False,
        )

    stored_github = epic.provider_metadata.get("github", {})
    stored_issue_id = stored_github.get("issue_id") or stored_github.get("id")
    if stored_issue_id:
        project_item: dict[str, Any] | None = None
        try:
            project_item = add_issue_to_project(project_id, str(stored_issue_id))
            update_project_item_status(
                project_id=project_id,
                project_item_id=project_item["id"],
                status=epic.status,
            )
            return _GitHubEpicProjection(
                issue={
                    "id": stored_issue_id,
                    "databaseId": stored_github.get("database_id"),
                    "number": stored_github.get("number"),
                    "url": stored_github.get("url"),
                },
                project_item=project_item,
                project_id=project_id,
                created_issue=False,
                created_project_item=True,
            )
        except Exception as exc:
            if project_item is not None:
                try:
                    delete_github_project_item(project_id, project_item["id"])
                except Exception as compensation_error:
                    raise TargetedBacklogMutationCompensationError(
                        "Epic projection repair failed and the new GitHub "
                        "project membership could not be removed. "
                        f"Original error: {exc}. "
                        f"Compensation error: {compensation_error}"
                    ) from compensation_error
            raise

    owner, name = _split_repository_name(epic.repository)
    github_repository = get_repository(owner, name)
    github_issue: dict[str, Any] | None = None

    try:
        github_issue = create_github_issue(
            repository_id=github_repository["id"],
            title=f"[Epic] {epic.title}",
            body=render_epic_body(epic),
        )
        project_item = add_issue_to_project(project_id, github_issue["id"])
        update_project_item_status(
            project_id=project_id,
            project_item_id=project_item["id"],
            status=epic.status,
        )
        return _GitHubEpicProjection(
            issue=github_issue,
            project_item=project_item,
            project_id=project_id,
            created_issue=True,
            created_project_item=True,
        )
    except Exception as exc:
        if github_issue is not None:
            _compensate_created_github_issue(
                issue_id=str(github_issue["id"]),
                original_error=exc,
            )
        raise


def _find_existing_github_epic(
    project_id: str,
    canonical_epic_id: str,
) -> dict[str, Any] | None:
    for row in list_project_issues(project_id):
        metadata = _extract_johnny_metadata(row.get("body", ""))
        if (
            metadata.get("id") == canonical_epic_id
            and metadata.get("type") == "epic"
        ):
            return row
    return None


def _hydrate_github_epic_metadata(
    epic: Epic,
    projection: _GitHubEpicProjection,
) -> None:
    issue = projection.issue
    project_item = projection.project_item
    current = epic.provider_metadata.get("github", {})
    epic.provider_metadata["github"] = {
        key: value
        for key, value in {
            **current,
            "issue_id": issue.get("id") or issue.get("issue_id"),
            "database_id": issue.get("databaseId")
            or issue.get("database_id"),
            "number": issue.get("number"),
            "url": issue.get("url"),
            "project_item_id": project_item.get("id")
            or project_item.get("project_item_id"),
            "project_id": projection.project_id,
        }.items()
        if value is not None
    }


def _github_project_id(backlog: Backlog) -> str:
    project_id = (
        backlog.project.provider_metadata
        .get("github", {})
        .get("project_id")
    )
    if not project_id:
        raise RuntimeError(
            "Canonical project is missing provider_metadata.github.project_id"
        )
    return str(project_id)


def _split_repository_name(repository_name: str) -> tuple[str, str]:
    parts = repository_name.split("/", maxsplit=1)
    if len(parts) != 2 or not all(parts):
        raise RuntimeError(
            "Repository must use the GitHub owner/name format: "
            f"{repository_name}"
        )
    return parts[0], parts[1]


def _extract_johnny_metadata(body: str) -> dict[str, str]:
    start = body.find("<!-- johnny-johnny")
    if start == -1:
        return {}

    end = body.find("-->", start)
    if end == -1:
        return {}

    result: dict[str, str] = {}
    for line in body[start:end].splitlines():
        line = line.strip()
        if not line or line.startswith("<!--") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _compensate_github_projection(
    *,
    projection: _GitHubEpicProjection,
    original_error: Exception,
) -> None:
    if projection.created_issue:
        _compensate_created_github_issue(
            issue_id=str(projection.issue["id"]),
            original_error=original_error,
        )
        return

    if projection.created_project_item:
        try:
            delete_github_project_item(
                projection.project_id,
                str(projection.project_item["id"]),
            )
        except Exception as compensation_error:
            raise TargetedBacklogMutationCompensationError(
                "Epic projection repair failed and the new GitHub project "
                "membership could not be removed. PostgreSQL was rolled back, "
                "but GitHub may contain an orphaned project item. "
                f"Original error: {original_error}. "
                f"Compensation error: {compensation_error}"
            ) from compensation_error


def _compensate_created_github_issue(
    *,
    issue_id: str,
    original_error: Exception,
) -> None:
    try:
        delete_github_issue(issue_id)
    except Exception as compensation_error:
        raise TargetedBacklogMutationCompensationError(
            "Epic creation failed and the new GitHub issue could not be "
            "deleted. PostgreSQL was rolled back, but GitHub may contain an "
            f"orphaned Johnny-Johnny epic. Original error: {original_error}. "
            f"Compensation error: {compensation_error}"
        ) from compensation_error



def preview_create_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    parent_epic_id: str,
    title: str,
    issue_id: str | None = None,
    description: str = "",
    repository_name: str | None = None,
    acceptance_criteria: list[str] | None = None,
    database_url: str | None = None,
) -> Issue:
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    return create_canonical_issue(
        backlog=backlog,
        title=title,
        epic_id=parent_epic_id,
        issue_id=issue_id,
        description=description,
        repository=repository_name,
        acceptance_criteria=acceptance_criteria or [],
    )


def create_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    parent_epic_id: str,
    title: str,
    issue_id: str | None = None,
    description: str = "",
    repository_name: str | None = None,
    acceptance_criteria: list[str] | None = None,
    database_url: str | None = None,
) -> tuple[Issue, Epic]:
    """Create or repair one issue in PostgreSQL and its GitHub projection."""
    _require_github_provider(provider)
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    state: _GitHubMutationState | None = None

    try:
        with repository.transaction() as transaction:
            backlog = transaction.load_backlog(location, lock_project=True)
            parent_epic = find_epic(backlog, parent_epic_id)
            resolved_issue_id = issue_id or _slugify_backlog_item_id(title)
            existing = _find_issue_and_parent(backlog, resolved_issue_id)

            if existing is None:
                issue = create_canonical_issue(
                    backlog=backlog,
                    title=title,
                    epic_id=parent_epic_id,
                    issue_id=resolved_issue_id,
                    description=description,
                    repository=repository_name,
                    acceptance_criteria=acceptance_criteria or [],
                )
                transaction.insert_issue(location, parent_epic_id, issue)
            else:
                issue, existing_parent = existing
                _assert_matching_issue_create_request(
                    issue=issue,
                    parent_epic=existing_parent,
                    requested_parent_epic_id=parent_epic_id,
                    title=title,
                    repository_name=repository_name or parent_epic.repository,
                    description=description,
                    acceptance_criteria=acceptance_criteria or [],
                )

            state = _synchronize_issue_projection(
                backlog=backlog,
                issue=issue,
                parent_epic=parent_epic,
            )
            transaction.save_item(
                location,
                issue,
                parent_epic_id=parent_epic.id,
            )
        return issue, parent_epic
    except Exception as exc:
        if state is not None:
            _compensate_github_mutation(state, exc)
        if isinstance(exc, RuntimeError):
            raise
        raise BacklogPersistenceError(
            f"PostgreSQL backlog persistence failed: {exc}"
        ) from exc


def preview_update_item_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    item_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    acceptance_criteria: list[str] | None = None,
    comment: str | None = None,
    database_url: str | None = None,
) -> Epic | Issue:
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    return update_canonical_item(
        backlog=backlog,
        issue_id=item_id,
        title=title,
        description=description,
        status=status,
        acceptance_criteria=acceptance_criteria,
        comment=comment,
    )


def update_item_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    item_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    acceptance_criteria: list[str] | None = None,
    comment: str | None = None,
    database_url: str | None = None,
) -> Epic | Issue:
    """Update one canonical item and its targeted GitHub projection."""
    _require_github_provider(provider)
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    state: _GitHubMutationState | None = None

    try:
        with repository.transaction() as transaction:
            backlog = transaction.load_backlog(location, lock_project=True)
            existing_item = find_backlog_item(backlog, item_id)
            previous_item = deepcopy(existing_item)
            parent_epic = (
                find_parent_epic(backlog, item_id)
                if isinstance(existing_item, Issue)
                else None
            )
            item = update_canonical_item(
                backlog=backlog,
                issue_id=item_id,
                title=title,
                description=description,
                status=status,
                acceptance_criteria=acceptance_criteria,
                comment=comment,
            )
            new_comment = item.comments[-1] if comment is not None else None
            state = _synchronize_item_update(
                backlog=backlog,
                item=item,
                previous_item=previous_item,
                parent_epic=parent_epic,
                new_comment=new_comment,
            )
            transaction.save_item(
                location,
                item,
                parent_epic_id=parent_epic.id if parent_epic else None,
            )
        return item
    except Exception as exc:
        if state is not None:
            _compensate_github_mutation(state, exc)
        if isinstance(exc, RuntimeError):
            raise
        raise BacklogPersistenceError(
            f"PostgreSQL backlog persistence failed: {exc}"
        ) from exc


def preview_move_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    issue_id: str,
    target_epic_id: str,
    database_url: str | None = None,
) -> tuple[Issue, Epic, Epic]:
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    source_epic = find_parent_epic(backlog, issue_id)
    target_epic = find_epic(backlog, target_epic_id)
    existing_issue = find_backlog_item(backlog, issue_id)
    if not isinstance(existing_issue, Issue):
        raise RuntimeError(f"Issue not found: {issue_id}")
    _assert_move_parent_supported(existing_issue, target_epic)
    issue = move_canonical_issue(backlog, issue_id, target_epic_id)
    return issue, source_epic, target_epic


def move_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    issue_id: str,
    target_epic_id: str,
    database_url: str | None = None,
) -> tuple[Issue, Epic, Epic]:
    """Move one canonical issue and replace its GitHub parent relationship."""
    _require_github_provider(provider)
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    state: _GitHubMutationState | None = None

    try:
        with repository.transaction() as transaction:
            backlog = transaction.load_backlog(location, lock_project=True)
            source_epic = find_parent_epic(backlog, issue_id)
            target_epic = find_epic(backlog, target_epic_id)
            existing_issue = find_backlog_item(backlog, issue_id)
            if not isinstance(existing_issue, Issue):
                raise RuntimeError(f"Issue not found: {issue_id}")
            _assert_move_parent_supported(existing_issue, target_epic)
            issue = move_canonical_issue(backlog, issue_id, target_epic_id)
            state = _synchronize_issue_move(
                backlog=backlog,
                issue=issue,
                source_epic=source_epic,
                target_epic=target_epic,
            )
            transaction.save_item(
                location,
                issue,
                parent_epic_id=target_epic.id,
            )
        return issue, source_epic, target_epic
    except Exception as exc:
        if state is not None:
            _compensate_github_mutation(state, exc)
        if isinstance(exc, RuntimeError):
            raise
        raise BacklogPersistenceError(
            f"PostgreSQL backlog persistence failed: {exc}"
        ) from exc


def preview_delete_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    issue_id: str,
    database_url: str | None = None,
) -> BacklogDeleteResult:
    """Preview deletion of one canonical issue and its provider projection."""
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    parent_epic = find_parent_epic(backlog, issue_id)
    issue = delete_canonical_issue(backlog, issue_id)
    return BacklogDeleteResult(
        issue=issue,
        parent_epic=parent_epic,
        github_issue_deleted=False,
    )


def delete_issue_in_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    issue_id: str,
    database_url: str | None = None,
) -> BacklogDeleteResult:
    """Delete one canonical issue and its GitHub projection.

    GitHub issue deletion is irreversible, so it cannot be compensated if the
    final PostgreSQL commit fails. In that edge case the canonical row remains
    and the command reports a retryable consistency error; rerunning the same
    delete completes the database side after confirming the provider issue is
    already absent.
    """
    _require_github_provider(provider)
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    github_issue_deleted = False

    try:
        with repository.transaction() as transaction:
            backlog = transaction.load_backlog(location, lock_project=True)
            parent_epic = find_parent_epic(backlog, issue_id)
            issue = find_backlog_item(backlog, issue_id)
            if not isinstance(issue, Issue):
                raise RuntimeError(f"Issue not found: {issue_id}")

            github_issue_id = _resolve_github_issue_id_for_delete(backlog, issue)
            if github_issue_id is not None:
                if _github_issue_exists(github_issue_id):
                    delete_github_issue(github_issue_id)
                    github_issue_deleted = True

            transaction.delete_issue(location, issue_id)

        return BacklogDeleteResult(
            issue=issue,
            parent_epic=parent_epic,
            github_issue_deleted=github_issue_deleted,
        )
    except Exception as exc:
        if github_issue_deleted:
            raise TargetedBacklogMutationConsistencyError(
                "GitHub issue deletion succeeded but PostgreSQL did not commit. "
                "The canonical issue may still exist without a provider "
                "projection. Rerun the same delete command to finish cleanup. "
                f"Original error: {exc}"
            ) from exc
        if isinstance(exc, RuntimeError):
            raise
        raise BacklogPersistenceError(
            f"PostgreSQL backlog persistence failed: {exc}"
        ) from exc


def preview_reconcile_backlog_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    max_operations: int | None,
    database_url: str | None = None,
) -> BacklogReconcilePreview:
    """Plan a bounded or complete provider reconciliation from PostgreSQL."""
    _require_github_provider(provider)
    if max_operations is not None and max_operations < 1:
        raise RuntimeError("max_operations must be at least 1")

    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    current_project_issues = list_project_issues(_github_project_id(backlog))
    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=current_project_issues,
    )
    execution_plan = _bounded_reconciliation_plan(plan, max_operations)
    return BacklogReconcilePreview(
        plan=plan,
        execution_plan=execution_plan,
        total_operation_count=len(plan.operations),
        execution_operation_count=len(execution_plan.operations),
        remaining_operation_count=(
            len(plan.operations) - len(execution_plan.operations)
        ),
    )


def reconcile_backlog_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    max_operations: int | None,
    database_url: str | None = None,
) -> BacklogReconcileResult:
    """Execute a bounded chunk or the complete reconciliation plan.

    Operations are grouped by canonical item so an issue creation chain is
    never split between runs. Each completed group persists hydrated provider
    metadata immediately, allowing the next run to resume safely.
    """
    _require_github_provider(provider)
    if max_operations is not None and max_operations < 1:
        raise RuntimeError("max_operations must be at least 1")

    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    metadata_before = _capture_provider_metadata(backlog, provider)
    current_project_issues = list_project_issues(_github_project_id(backlog))
    plan = plan_reconcile_backlog(
        backlog=backlog,
        current_project_issues=current_project_issues,
    )
    execution_plan = _bounded_reconciliation_plan(plan, max_operations)
    preview = BacklogReconcilePreview(
        plan=plan,
        execution_plan=execution_plan,
        total_operation_count=len(plan.operations),
        execution_operation_count=len(execution_plan.operations),
        remaining_operation_count=(
            len(plan.operations) - len(execution_plan.operations)
        ),
    )

    hydrated_items = _items_with_changed_provider_metadata(
        backlog,
        provider,
        metadata_before,
    )
    if hydrated_items:
        _persist_reconciled_items(
            repository=repository,
            location=location,
            backlog=backlog,
            items=hydrated_items,
        )

    groups = _group_reconciliation_operations(execution_plan.operations)
    for index, group in enumerate(groups):
        _execute_reconciliation_group(
            repository=repository,
            location=location,
            backlog=backlog,
            group=group,
            announce=index == 0,
        )

    return BacklogReconcileResult(
        preview=preview,
        executed_group_count=len(groups),
        hydrated_item_count=len(hydrated_items),
    )


def preview_purge_backlog_projection(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    max_issues: int | None,
    database_url: str | None = None,
) -> BacklogPurgeResult:
    """Preview a bounded or complete GitHub projection purge."""
    _require_github_provider(provider)
    if max_issues is not None and max_issues < 1:
        raise RuntimeError("max_issues must be at least 1")
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    all_issues = tuple(_johnny_managed_project_issues(backlog))
    selected = all_issues if max_issues is None else all_issues[:max_issues]
    return BacklogPurgeResult(
        project_title=provider_project_title,
        issues=selected,
        total_issue_count=len(all_issues),
        deleted_issue_count=0,
        remaining_issue_count=len(all_issues) - len(selected),
        cleared_item_count=0,
        projection_metadata_cleared=False,
    )


def purge_backlog_projection_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    max_issues: int | None,
    database_url: str | None = None,
) -> BacklogPurgeResult:
    """Delete a bounded or complete GitHub projection and retain canonical data.

    Canonical rows are never deleted. Provider metadata is cleared only after
    the final visible Johnny-managed issue has been deleted, making repeated
    runs resumable after provider throttling or process interruption.
    """
    _require_github_provider(provider)
    if max_issues is not None and max_issues < 1:
        raise RuntimeError("max_issues must be at least 1")
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    all_issues = tuple(_johnny_managed_project_issues(backlog))
    selected = all_issues if max_issues is None else all_issues[:max_issues]

    deleted_count = 0
    for issue in selected:
        delete_github_issue(str(issue["id"]))
        deleted_count += 1

    remaining_count = len(all_issues) - deleted_count
    cleared_item_count = 0
    metadata_cleared = False
    if remaining_count == 0:
        try:
            with repository.transaction() as transaction:
                cleared_item_count = transaction.clear_provider_projection_metadata(
                    location,
                    provider,
                )
            metadata_cleared = True
        except Exception as exc:
            raise TargetedBacklogMutationConsistencyError(
                "GitHub projection purge completed but PostgreSQL provider "
                "metadata was not cleared. Canonical data remains intact. "
                "Rerun the same purge command to finish cleanup. "
                f"Original error: {exc}"
            ) from exc

    return BacklogPurgeResult(
        project_title=provider_project_title,
        issues=selected,
        total_issue_count=len(all_issues),
        deleted_issue_count=deleted_count,
        remaining_issue_count=remaining_count,
        cleared_item_count=cleared_item_count,
        projection_metadata_cleared=metadata_cleared,
    )


def _execute_reconciliation_group(
    *,
    repository: PostgresBacklogRepository,
    location: BacklogLocation,
    backlog: Backlog,
    group: tuple[BacklogOperation, ...],
    announce: bool,
) -> None:
    """Execute and persist one item-sized group with provider compensation."""
    try:
        execute_reconciliation_plan(
            plan=ExecutionPlan(operations=list(group)),
            project_title=backlog.project.title,
            project_id=_github_project_id(backlog),
            announce=announce,
        )
        affected_items = _canonical_items_for_operations(backlog, group)
        if affected_items:
            _persist_reconciled_items(
                repository=repository,
                location=location,
                backlog=backlog,
                items=affected_items,
            )
    except Exception as exc:
        _compensate_reconciliation_group(
            backlog=backlog,
            group=group,
            original_error=exc,
        )
        raise


def _compensate_reconciliation_group(
    *,
    backlog: Backlog,
    group: tuple[BacklogOperation, ...],
    original_error: Exception,
) -> None:
    """Best-effort restore of provider state for one failed reconcile group."""
    created_item = next(
        (
            operation.epic
            if isinstance(operation, CreateEpicOperation)
            else operation.issue
            for operation in group
            if isinstance(operation, (CreateEpicOperation, CreateIssueOperation))
        ),
        None,
    )
    if created_item is not None:
        issue_id = _stored_github_issue_id(created_item)
        if not issue_id:
            return
        try:
            delete_github_issue(issue_id)
            return
        except Exception as compensation_error:
            raise TargetedBacklogMutationCompensationError(
                "Reconciliation failed and the partially created GitHub issue "
                "could not be deleted. PostgreSQL was not updated, but GitHub "
                f"may contain an orphan. Original error: {original_error}. "
                f"Compensation error: {compensation_error}"
            ) from compensation_error

    compensation_errors: list[str] = []
    for operation in group:
        if not isinstance(operation, CreateCommentOperation):
            continue
        comment_id = (
            operation.comment.provider_metadata
            .get("github", {})
            .get("comment_id")
        )
        if not comment_id:
            continue
        try:
            delete_github_issue_comment(str(comment_id))
        except Exception as exc:
            compensation_errors.append(f"delete comment {operation.comment.id}: {exc}")

    status_operation = next(
        (
            operation
            for operation in group
            if isinstance(operation, UpdateIssueStatusOperation)
        ),
        None,
    )
    if status_operation is not None:
        github = status_operation.issue.provider_metadata.get("github", {})
        project_item_id = github.get("project_item_id")
        if project_item_id:
            try:
                if status_operation.current_status is None:
                    clear_project_item_status(
                        project_id=_github_project_id(backlog),
                        project_item_id=str(project_item_id),
                    )
                else:
                    update_project_item_status(
                        project_id=_github_project_id(backlog),
                        project_item_id=str(project_item_id),
                        status=status_operation.current_status,
                    )
            except Exception as exc:
                compensation_errors.append(f"restore status: {exc}")

    if compensation_errors:
        raise TargetedBacklogMutationCompensationError(
            "Reconciliation failed and GitHub compensation was incomplete. "
            "PostgreSQL was not updated, but provider drift may remain. "
            f"Original error: {original_error}. Compensation errors: "
            + "; ".join(compensation_errors)
        )


def _resolve_github_issue_id_for_delete(
    backlog: Backlog,
    issue: Issue,
) -> str | None:
    stored_id = _stored_github_issue_id(issue)
    if stored_id:
        return stored_id

    live = _find_live_github_item(
        list_project_issues(_github_project_id(backlog)),
        issue.id,
    )
    if live is None:
        return None
    value = live.get("id") or live.get("issue_id")
    return str(value) if value else None


def _github_issue_exists(issue_id: str) -> bool:
    try:
        get_github_issue(issue_id)
        return True
    except RuntimeError as exc:
        message = str(exc)
        if (
            message == f"GitHub issue not found: {issue_id}"
            or "Could not resolve to a node" in message
            or "could not resolve to a node" in message
        ):
            return False
        raise


def _bounded_reconciliation_plan(
    plan: ExecutionPlan,
    max_operations: int | None,
) -> ExecutionPlan:
    if max_operations is None:
        return ExecutionPlan(operations=list(plan.operations))

    selected: list[BacklogOperation] = []
    for group in _group_reconciliation_operations(plan.operations):
        if selected and len(selected) + len(group) > max_operations:
            break
        selected.extend(group)
        if len(selected) >= max_operations:
            break
    return ExecutionPlan(operations=selected)


def _group_reconciliation_operations(
    operations: list[BacklogOperation],
) -> list[tuple[BacklogOperation, ...]]:
    groups: list[tuple[BacklogOperation, ...]] = []
    current: list[BacklogOperation] = []
    current_item_id: str | None = None

    for operation in operations:
        item_id = _reconciliation_operation_item_id(operation)
        if current and item_id != current_item_id:
            groups.append(tuple(current))
            current = []
        current.append(operation)
        current_item_id = item_id

    if current:
        groups.append(tuple(current))
    return groups


def _reconciliation_operation_item_id(operation: BacklogOperation) -> str:
    if isinstance(operation, CreateEpicOperation):
        return operation.epic.id
    if isinstance(operation, CreateIssueOperation):
        return operation.issue.id
    if isinstance(operation, AddIssueToProjectOperation):
        return operation.issue.id
    if isinstance(operation, AttachIssueToEpicOperation):
        return operation.issue.id
    if isinstance(operation, UpdateIssueStatusOperation):
        return operation.issue.id
    if isinstance(operation, CreateCommentOperation):
        return operation.item.id
    if isinstance(operation, DeleteIssueOperation):
        return operation.issue.id
    raise RuntimeError(
        f"Unsupported reconciliation operation: {type(operation).__name__}"
    )


def _canonical_items_for_operations(
    backlog: Backlog,
    operations: tuple[BacklogOperation, ...],
) -> list[Epic | Issue]:
    items: list[Epic | Issue] = []
    seen: set[str] = set()
    for operation in operations:
        if isinstance(operation, DeleteIssueOperation):
            continue
        item_id = _reconciliation_operation_item_id(operation)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(find_backlog_item(backlog, item_id))
    return items


def _persist_reconciled_items(
    *,
    repository: PostgresBacklogRepository,
    location: BacklogLocation,
    backlog: Backlog,
    items: list[Epic | Issue],
) -> None:
    with repository.transaction() as transaction:
        for item in items:
            parent_epic_id = (
                find_parent_epic(backlog, item.id).id
                if isinstance(item, Issue)
                else None
            )
            transaction.save_item(
                location,
                item,
                parent_epic_id=parent_epic_id,
            )


def _capture_provider_metadata(
    backlog: Backlog,
    provider: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in _all_backlog_items(backlog):
        result[item.id] = {
            "item": deepcopy(item.provider_metadata.get(provider, {})),
            "comments": {
                comment.id: deepcopy(comment.provider_metadata.get(provider, {}))
                for comment in item.comments
            },
        }
    return result


def _items_with_changed_provider_metadata(
    backlog: Backlog,
    provider: str,
    before: dict[str, Any],
) -> list[Epic | Issue]:
    changed: list[Epic | Issue] = []
    for item in _all_backlog_items(backlog):
        current = {
            "item": item.provider_metadata.get(provider, {}),
            "comments": {
                comment.id: comment.provider_metadata.get(provider, {})
                for comment in item.comments
            },
        }
        if current != before.get(item.id):
            changed.append(item)
    return changed


def _all_backlog_items(backlog: Backlog) -> list[Epic | Issue]:
    return [
        item
        for epic in backlog.epics
        for item in (epic, *epic.issues)
    ]


def _johnny_managed_project_issues(backlog: Backlog) -> list[dict[str, Any]]:
    managed = [
        issue
        for issue in list_project_issues(_github_project_id(backlog))
        if "<!-- johnny-johnny" in (issue.get("body") or "")
    ]
    return sorted(
        managed,
        key=lambda issue: (
            1 if _extract_johnny_metadata(issue.get("body") or "").get("type") == "epic" else 0,
            -(int(issue.get("number") or 0)),
        ),
    )


def _synchronize_issue_projection(
    *,
    backlog: Backlog,
    issue: Issue,
    parent_epic: Epic,
) -> _GitHubMutationState:
    project_id = _github_project_id(backlog)
    rows = list_project_issues(project_id)
    live_issue = _find_live_github_item(rows, issue.id)
    state = _GitHubMutationState(project_id=project_id)

    try:
        if live_issue is not None:
            github_issue = live_issue
            state.project_item_id = str(live_issue["project_item_id"])
            state.prior_status = live_issue.get("project_status")
        else:
            stored_id = _stored_github_issue_id(issue)
            if stored_id:
                github_issue = get_github_issue(stored_id)
            else:
                owner, name = _split_repository_name(issue.repository)
                github_repository = get_repository(owner, name)
                github_issue = create_github_issue(
                    repository_id=github_repository["id"],
                    title=issue.title,
                    body=render_issue_body(issue, parent_epic),
                )
                state.created_issue = True

            state.issue = github_issue
            project_item = add_issue_to_project(project_id, github_issue["id"])
            state.project_item_id = str(project_item["id"])
            state.created_project_item = True

        state.issue = github_issue
        state.prior_title = github_issue.get("title")
        state.prior_body = github_issue.get("body")
        _apply_github_content(
            state,
            title=issue.title,
            body=render_issue_body(issue, parent_epic),
        )
        _apply_github_status(state, issue.status)
        _apply_github_parent(
            state,
            child=issue,
            target_parent=_resolve_github_item(rows, parent_epic),
        )
        _hydrate_github_item_metadata(issue, state)
        return state
    except Exception as exc:
        _compensate_github_mutation(state, exc)
        raise


def _synchronize_item_update(
    *,
    backlog: Backlog,
    item: Epic | Issue,
    previous_item: Epic | Issue,
    parent_epic: Epic | None,
    new_comment: Any | None,
) -> _GitHubMutationState:
    project_id = _github_project_id(backlog)
    rows = list_project_issues(project_id)
    live_issue = _find_live_github_item(rows, item.id)
    state = _GitHubMutationState(project_id=project_id)

    try:
        if live_issue is None:
            stored_id = _stored_github_issue_id(item)
            if not stored_id:
                raise RuntimeError(
                    f"GitHub projection not found for canonical {item.type}: {item.id}"
                )
            github_issue = get_github_issue(stored_id)
            project_item = add_issue_to_project(project_id, github_issue["id"])
            state.created_project_item = True
            state.project_item_id = str(project_item["id"])
        else:
            github_issue = live_issue
            state.project_item_id = str(live_issue["project_item_id"])
            state.prior_status = live_issue.get("project_status")

        state.issue = github_issue
        state.prior_title = github_issue.get("title")
        state.prior_body = github_issue.get("body")
        desired_title = f"[Epic] {item.title}" if isinstance(item, Epic) else item.title
        desired_body = (
            render_epic_body(item)
            if isinstance(item, Epic)
            else render_issue_body(item, _required_parent(parent_epic))
        )
        _apply_github_content(state, title=desired_title, body=desired_body)
        _apply_github_status(state, item.status)

        if new_comment is not None:
            github_comment = create_issue_comment(
                issue_id=str(github_issue["id"]),
                body=render_comment_body(item, new_comment),
            )
            state.created_comment_id = str(github_comment["id"])
            _hydrate_github_comment_metadata(new_comment, github_comment)

        _hydrate_github_item_metadata(item, state)
        return state
    except Exception as exc:
        _compensate_github_mutation(state, exc)
        raise


def _synchronize_issue_move(
    *,
    backlog: Backlog,
    issue: Issue,
    source_epic: Epic,
    target_epic: Epic,
) -> _GitHubMutationState:
    project_id = _github_project_id(backlog)
    rows = list_project_issues(project_id)
    live_issue = _find_live_github_item(rows, issue.id)
    if live_issue is None:
        raise RuntimeError(f"GitHub projection not found for canonical issue: {issue.id}")

    state = _GitHubMutationState(
        issue=live_issue,
        project_id=project_id,
        project_item_id=str(live_issue["project_item_id"]),
        prior_title=live_issue.get("title"),
        prior_body=live_issue.get("body"),
        prior_status=live_issue.get("project_status"),
    )
    try:
        _apply_github_parent(
            state,
            child=issue,
            target_parent=_resolve_github_item(rows, target_epic),
        )
        _apply_github_content(
            state,
            title=issue.title,
            body=render_issue_body(issue, target_epic),
        )
        _hydrate_github_item_metadata(issue, state)
        return state
    except Exception as exc:
        _compensate_github_mutation(state, exc)
        raise


def _apply_github_content(
    state: _GitHubMutationState,
    *,
    title: str,
    body: str,
) -> None:
    issue = _required_github_issue(state)
    if issue.get("title") == title and (issue.get("body") or "") == body:
        return
    updated = update_github_issue(
        str(issue["id"]),
        title=title,
        body=body,
    )
    state.issue = {**issue, **updated}
    state.content_changed = True


def _apply_github_status(
    state: _GitHubMutationState,
    status: str,
) -> None:
    if not state.project_id or not state.project_item_id:
        raise RuntimeError("GitHub project item metadata is incomplete")
    if state.prior_status == status and not state.created_project_item:
        return
    update_project_item_status(
        project_id=state.project_id,
        project_item_id=state.project_item_id,
        status=status,
    )
    state.status_changed = True


def _apply_github_parent(
    state: _GitHubMutationState,
    *,
    child: Issue,
    target_parent: dict[str, Any],
) -> None:
    issue = _required_github_issue(state)
    prior_parent = get_github_issue_parent(str(issue["id"]))
    state.prior_parent = prior_parent
    state.target_parent = target_parent
    if prior_parent and prior_parent.get("id") == target_parent.get("id"):
        return
    owner, repo = _split_repository_name(target_parent["repository"])
    add_sub_issue(
        owner=owner,
        repo=repo,
        parent_issue_number=int(target_parent["number"]),
        child_issue_database_id=_github_database_id(issue),
        replace_parent=True,
    )
    state.parent_changed = True


def _compensate_github_mutation(
    state: _GitHubMutationState,
    original_error: Exception,
) -> None:
    if state.created_issue and state.issue is not None:
        try:
            delete_github_issue(str(state.issue["id"]))
            return
        except Exception as compensation_error:
            raise TargetedBacklogMutationCompensationError(
                "Targeted backlog mutation failed and the new GitHub issue "
                "could not be deleted. PostgreSQL was rolled back, but "
                f"GitHub may contain an orphan. Original error: {original_error}. "
                f"Compensation error: {compensation_error}"
            ) from compensation_error

    compensation_errors: list[str] = []
    if state.created_comment_id:
        try:
            delete_github_issue_comment(state.created_comment_id)
        except Exception as exc:
            compensation_errors.append(f"delete comment: {exc}")

    if state.parent_changed and state.issue is not None:
        try:
            _restore_github_parent(state)
        except Exception as exc:
            compensation_errors.append(f"restore parent: {exc}")

    if (
        state.status_changed
        and not state.created_project_item
        and state.project_id
        and state.project_item_id
    ):
        try:
            if state.prior_status is None:
                clear_project_item_status(
                    project_id=state.project_id,
                    project_item_id=state.project_item_id,
                )
            else:
                update_project_item_status(
                    project_id=state.project_id,
                    project_item_id=state.project_item_id,
                    status=state.prior_status,
                )
        except Exception as exc:
            compensation_errors.append(f"restore status: {exc}")

    if state.content_changed and state.issue is not None:
        try:
            update_github_issue(
                str(state.issue["id"]),
                title=state.prior_title,
                body=state.prior_body,
            )
        except Exception as exc:
            compensation_errors.append(f"restore issue content: {exc}")

    if state.created_project_item and state.project_id and state.project_item_id:
        try:
            delete_github_project_item(state.project_id, state.project_item_id)
        except Exception as exc:
            compensation_errors.append(f"remove project item: {exc}")

    if compensation_errors:
        raise TargetedBacklogMutationCompensationError(
            "Targeted backlog mutation failed and GitHub compensation was "
            "incomplete. PostgreSQL was rolled back, but provider drift may "
            f"remain. Original error: {original_error}. Compensation errors: "
            + "; ".join(compensation_errors)
        )


def _restore_github_parent(state: _GitHubMutationState) -> None:
    issue = _required_github_issue(state)
    child_database_id = _github_database_id(issue)
    if state.prior_parent:
        owner, repo = _split_repository_name(state.prior_parent["repository"]["nameWithOwner"])
        add_sub_issue(
            owner=owner,
            repo=repo,
            parent_issue_number=int(state.prior_parent["number"]),
            child_issue_database_id=child_database_id,
            replace_parent=True,
        )
        return
    if state.target_parent:
        owner, repo = _split_repository_name(state.target_parent["repository"])
        remove_sub_issue(
            owner=owner,
            repo=repo,
            parent_issue_number=int(state.target_parent["number"]),
            child_issue_database_id=child_database_id,
        )


def _hydrate_github_item_metadata(
    item: Epic | Issue,
    state: _GitHubMutationState,
) -> None:
    issue = _required_github_issue(state)
    current = item.provider_metadata.get("github", {})
    item.provider_metadata["github"] = {
        key: value
        for key, value in {
            **current,
            "issue_id": issue.get("id"),
            "database_id": issue.get("databaseId") or issue.get("database_id"),
            "number": issue.get("number"),
            "url": issue.get("url"),
            "project_item_id": state.project_item_id,
            "project_id": state.project_id,
        }.items()
        if value is not None
    }


def _hydrate_github_comment_metadata(comment: Any, github_comment: dict[str, Any]) -> None:
    current = comment.provider_metadata.get("github", {})
    comment.provider_metadata["github"] = {
        key: value
        for key, value in {
            **current,
            "comment_id": github_comment.get("id"),
            "database_id": github_comment.get("databaseId"),
            "url": github_comment.get("url"),
            "created_at": github_comment.get("createdAt"),
            "updated_at": github_comment.get("updatedAt"),
        }.items()
        if value is not None
    }


def _find_live_github_item(
    rows: list[dict[str, Any]],
    canonical_id: str,
) -> dict[str, Any] | None:
    for row in rows:
        metadata = _extract_johnny_metadata(row.get("body", ""))
        if metadata.get("id") == canonical_id:
            return row
    return None


def _resolve_github_item(
    rows: list[dict[str, Any]],
    item: Epic | Issue,
) -> dict[str, Any]:
    live = _find_live_github_item(rows, item.id)
    if live is not None:
        return {
            **live,
            "repository": live.get("repository") or item.repository,
        }
    stored_id = _stored_github_issue_id(item)
    if not stored_id:
        raise RuntimeError(f"GitHub projection not found for canonical {item.type}: {item.id}")
    github_issue = get_github_issue(stored_id)
    return {
        **github_issue,
        "repository": github_issue["repository"]["nameWithOwner"],
    }


def _stored_github_issue_id(item: Epic | Issue) -> str | None:
    github = item.provider_metadata.get("github", {})
    value = github.get("issue_id") or github.get("id")
    return str(value) if value else None


def _required_github_issue(state: _GitHubMutationState) -> dict[str, Any]:
    if state.issue is None:
        raise RuntimeError("GitHub issue metadata is incomplete")
    return state.issue


def _github_database_id(issue: dict[str, Any]) -> int:
    value = issue.get("databaseId") or issue.get("database_id")
    if value is None:
        raise RuntimeError("GitHub issue database id is missing")
    return int(value)


def _required_parent(parent_epic: Epic | None) -> Epic:
    if parent_epic is None:
        raise RuntimeError("Parent epic is required for a canonical issue")
    return parent_epic


def _require_github_provider(provider: str) -> None:
    if provider != "github":
        raise RuntimeError(
            "Targeted canonical mutations currently support provider: github"
        )


def _find_issue_and_parent(
    backlog: Backlog,
    issue_id: str,
) -> tuple[Issue, Epic] | None:
    for epic in backlog.epics:
        for issue in epic.issues:
            if issue.id == issue_id:
                return issue, epic
    return None


def _assert_matching_issue_create_request(
    *,
    issue: Issue,
    parent_epic: Epic,
    requested_parent_epic_id: str,
    title: str,
    repository_name: str,
    description: str,
    acceptance_criteria: list[str],
) -> None:
    differences: list[str] = []
    if parent_epic.id != requested_parent_epic_id:
        differences.append("parent epic")
    if issue.title != title:
        differences.append("title")
    if issue.repository != repository_name:
        differences.append("repository")
    if issue.description != description:
        differences.append("description")
    if issue.acceptance_criteria != acceptance_criteria:
        differences.append("acceptance criteria")
    if differences:
        raise RuntimeError(
            f"Backlog item already exists with different {', '.join(differences)}: "
            f"{issue.id}"
        )


def _assert_move_parent_supported(
    issue: Issue,
    target_epic: Epic,
) -> None:
    issue_owner, _ = _split_repository_name(issue.repository)
    target_owner, _ = _split_repository_name(target_epic.repository)
    if issue_owner.lower() != target_owner.lower():
        raise RuntimeError(
            "GitHub sub-issues must share a repository owner. Moving this "
            "issue to the selected epic would cross GitHub owners."
        )

def import_backlog_to_postgres(
    *,
    backlog: Backlog,
    user_display_name: str,
    user_primary_email: str | None,
    provider_account_username: str,
    provider_account_display_name: str | None,
    database_url: str | None = None,
    verify: bool = True,
) -> BacklogImportResult:
    """Replace one canonical snapshot from an explicit import document."""
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    return repository.replace(
        backlog,
        user_display_name=user_display_name,
        user_primary_email=user_primary_email,
        provider_account_username=provider_account_username,
        provider_account_display_name=provider_account_display_name,
        verify=verify,
    )


def import_backlog_yaml_text_to_postgres(
    *,
    backlog_yaml: str,
    user_display_name: str,
    user_primary_email: str | None,
    provider_account_username: str,
    provider_account_display_name: str | None,
    database_url: str | None = None,
    verify: bool = True,
) -> BacklogImportResult:
    backlog = load_backlog_yaml_text(backlog_yaml)
    return import_backlog_to_postgres(
        backlog=backlog,
        user_display_name=user_display_name,
        user_primary_email=user_primary_email,
        provider_account_username=provider_account_username,
        provider_account_display_name=provider_account_display_name,
        database_url=database_url,
        verify=verify,
    )


def import_backlog_yaml_to_postgres(
    *,
    backlog_path: str,
    user_display_name: str,
    user_primary_email: str | None,
    provider_account_username: str,
    provider_account_display_name: str | None,
    database_url: str | None = None,
    verify: bool = True,
) -> BacklogImportResult:
    backlog = load_backlog_yaml(backlog_path)
    return import_backlog_to_postgres(
        backlog=backlog,
        user_display_name=user_display_name,
        user_primary_email=user_primary_email,
        provider_account_username=provider_account_username,
        provider_account_display_name=provider_account_display_name,
        database_url=database_url,
        verify=verify,
    )


def export_backlog_yaml_text_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    database_url: str | None = None,
) -> BacklogYamlExportResult:
    """Render one canonical PostgreSQL backlog as portable YAML text."""
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    return BacklogYamlExportResult(
        location=location,
        content=render_backlog_yaml(backlog),
        epic_count=len(backlog.epics),
        issue_count=sum(len(epic.issues) for epic in backlog.epics),
        comment_count=sum(
            len(epic.comments) + sum(len(issue.comments) for issue in epic.issues)
            for epic in backlog.epics
        ),
    )


def export_backlog_yaml_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    output_path: str,
    database_url: str | None = None,
) -> BacklogExportResult:
    rendered = export_backlog_yaml_text_from_postgres(
        provider=provider,
        provider_account_username=provider_account_username,
        provider_project_title=provider_project_title,
        database_url=database_url,
    )
    # Keep filesystem output in the CLI-oriented adapter while reusing the same
    # PostgreSQL load and YAML rendering workflow as the REST API.
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(rendered.content, encoding="utf-8")

    return BacklogExportResult(
        location=rendered.location,
        output_path=output_path,
        epic_count=rendered.epic_count,
        issue_count=rendered.issue_count,
        comment_count=rendered.comment_count,
    )
