from pathlib import Path
from typing import Any

import yaml

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue, Project


def load_backlog_yaml(backlog_path: str) -> Backlog:
    backlog_file = Path(backlog_path)

    if not backlog_file.exists():
        raise RuntimeError(f"Backlog YAML not found: {backlog_file}")

    data = yaml.safe_load(backlog_file.read_text(encoding="utf-8")) or {}

    project_data = data["project"]

    epics = []
    for epic_data in data.get("epics", []):
        issues = [
            _load_issue(issue_data)
            for issue_data in epic_data.get("issues", [])
        ]

        epics.append(
            Epic(
                id=epic_data["id"],
                type=epic_data["type"],
                title=epic_data["title"],
                repository=epic_data["repository"],
                status=epic_data["status"],
                order=epic_data["order"],
                description=epic_data.get("description", ""),
                acceptance_criteria=_list(epic_data, "acceptance_criteria"),
                labels=_list(epic_data, "labels"),
                assignees=_list(epic_data, "assignees"),
                milestone=epic_data.get("milestone"),
                provider_metadata=epic_data.get("provider_metadata", {}),
                issues=issues,
            )
        )

    return Backlog(
        project=Project(
            provider=project_data["provider"],
            title=project_data["title"],
            number=project_data.get("number"),
            url=project_data.get("url"),
            provider_metadata=project_data.get("provider_metadata", {}),
        ),
        epics=epics,
    )


def _load_issue(issue_data: dict[str, Any]) -> Issue:
    return Issue(
        id=issue_data["id"],
        type=issue_data["type"],
        title=issue_data["title"],
        repository=issue_data["repository"],
        status=issue_data["status"],
        order=issue_data["order"],
        description=issue_data.get("description", ""),
        acceptance_criteria=_list(issue_data, "acceptance_criteria"),
        labels=_list(issue_data, "labels"),
        assignees=_list(issue_data, "assignees"),
        milestone=issue_data.get("milestone"),
        provider_metadata=issue_data.get("provider_metadata", {}),
    )


def _list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)

    if value is None:
        return []

    return list(value)