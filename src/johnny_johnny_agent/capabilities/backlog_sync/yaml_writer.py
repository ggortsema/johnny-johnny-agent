from pathlib import Path
from typing import Any

import yaml

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


def save_backlog_yaml(
        backlog: Backlog,
        backlog_path: str,
) -> None:
    backlog_file = Path(backlog_path)
    backlog_file.parent.mkdir(parents=True, exist_ok=True)

    backlog_file.write_text(
        yaml.safe_dump(
            _backlog_to_dict(backlog),
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )


def _backlog_to_dict(backlog: Backlog) -> dict[str, Any]:
    return {
        "version": 1,
        "project": {
            "provider": backlog.project.provider,
            "title": backlog.project.title,
            "number": backlog.project.number,
            "url": backlog.project.url,
            "provider_metadata": backlog.project.provider_metadata,
        },
        "epics": [
            _epic_to_dict(epic)
            for epic in sorted(backlog.epics, key=lambda item: item.order)
        ],
    }


def _epic_to_dict(epic: Epic) -> dict[str, Any]:
    return {
        "id": epic.id,
        "type": epic.type,
        "title": epic.title,
        "repository": epic.repository,
        "status": epic.status,
        "issue_state": epic.issue_state,
        "order": epic.order,
        "description": epic.description,
        "acceptance_criteria": epic.acceptance_criteria,
        "labels": epic.labels,
        "assignees": epic.assignees,
        "milestone": epic.milestone,
        "provider_metadata": epic.provider_metadata,
        "issues": [
            _issue_to_dict(issue)
            for issue in sorted(epic.issues, key=lambda item: item.order)
        ],
    }


def _issue_to_dict(issue: Issue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "type": issue.type,
        "title": issue.title,
        "repository": issue.repository,
        "status": issue.status,
        "issue_state": issue.issue_state,
        "order": issue.order,
        "description": issue.description,
        "acceptance_criteria": issue.acceptance_criteria,
        "labels": issue.labels,
        "assignees": issue.assignees,
        "milestone": issue.milestone,
        "provider_metadata": issue.provider_metadata,
    }