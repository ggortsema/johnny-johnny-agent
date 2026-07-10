"""Application workflows for PostgreSQL canonical backlog persistence."""

from __future__ import annotations

from dataclasses import dataclass

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogImportResult,
    BacklogLocation,
    DatabaseStatus,
    PostgresBacklogRepository,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_loader import load_backlog_yaml
from johnny_johnny_agent.capabilities.backlog_sync.yaml_writer import save_backlog_yaml
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


def summarize_backlog(backlog: Backlog) -> BacklogSummary:
    items: list[Epic | Issue] = []
    for epic in backlog.epics:
        items.append(epic)
        items.extend(epic.issues)

    return BacklogSummary(
        epic_count=len(backlog.epics),
        issue_count=sum(len(epic.issues) for epic in backlog.epics),
        acceptance_criterion_count=sum(
            len(item.acceptance_criteria) for item in items
        ),
        comment_count=sum(len(item.comments) for item in items),
        label_count=sum(len(item.labels) for item in items),
        assignee_count=sum(len(item.assignees) for item in items),
    )


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
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    return repository.replace(
        backlog,
        user_display_name=user_display_name,
        user_primary_email=user_primary_email,
        provider_account_username=provider_account_username,
        provider_account_display_name=provider_account_display_name,
        verify=verify,
    )


def export_backlog_yaml_from_postgres(
    *,
    provider: str,
    provider_account_username: str,
    provider_project_title: str,
    output_path: str,
    database_url: str | None = None,
) -> BacklogExportResult:
    location = BacklogLocation(
        provider=provider,
        provider_account_username=provider_account_username,
        project_title=provider_project_title,
    )
    repository = PostgresBacklogRepository(resolve_database_url(database_url))
    backlog = repository.load(location)
    save_backlog_yaml(backlog, output_path)

    return BacklogExportResult(
        location=location,
        output_path=output_path,
        epic_count=len(backlog.epics),
        issue_count=sum(len(epic.issues) for epic in backlog.epics),
        comment_count=sum(
            len(epic.comments) + sum(len(issue.comments) for issue in epic.issues)
            for epic in backlog.epics
        ),
    )
