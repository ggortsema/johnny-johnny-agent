"""Load canonical backlog documents from explicit YAML boundaries."""

from pathlib import Path
from typing import Any, Mapping

import yaml

from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue, Project


def load_backlog_yaml(backlog_path: str) -> Backlog:
    backlog_file = Path(backlog_path)

    if not backlog_file.exists():
        raise RuntimeError(f"Backlog YAML not found: {backlog_file}")

    return load_backlog_yaml_text(backlog_file.read_text(encoding="utf-8"))


def load_backlog_yaml_text(backlog_yaml: str) -> Backlog:
    """Parse a canonical backlog from YAML text without implying runtime storage."""
    data = yaml.safe_load(backlog_yaml) or {}
    if not isinstance(data, Mapping):
        raise RuntimeError("Backlog YAML root must be a mapping.")
    return load_backlog_document(data)


def load_backlog_document(data: Mapping[str, Any]) -> Backlog:
    """Build the canonical domain model from an already-parsed document."""
    project_data = _mapping(data["project"], "project")

    epics = []
    for raw_epic_data in data.get("epics", []) or []:
        epic_data = _mapping(raw_epic_data, "epic")
        issues = [
            _load_issue(_mapping(issue_data, "issue"))
            for issue_data in epic_data.get("issues", []) or []
        ]

        epics.append(
            Epic(
                id=epic_data["id"],
                type=epic_data["type"],
                title=epic_data["title"],
                repository=epic_data["repository"],
                status=epic_data["status"],
                issue_state=epic_data["issue_state"],
                order=epic_data["order"],
                description=epic_data.get("description", ""),
                acceptance_criteria=_list(epic_data, "acceptance_criteria"),
                comments=_load_comments(epic_data),
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


def _load_issue(issue_data: Mapping[str, Any]) -> Issue:
    return Issue(
        id=issue_data["id"],
        type=issue_data["type"],
        title=issue_data["title"],
        repository=issue_data["repository"],
        status=issue_data["status"],
        issue_state=issue_data["issue_state"],
        order=issue_data["order"],
        description=issue_data.get("description", ""),
        acceptance_criteria=_list(issue_data, "acceptance_criteria"),
        comments=_load_comments(issue_data),
        labels=_list(issue_data, "labels"),
        assignees=_list(issue_data, "assignees"),
        milestone=issue_data.get("milestone"),
        provider_metadata=issue_data.get("provider_metadata", {}),
    )


def _load_comments(data: Mapping[str, Any]) -> list[Comment]:
    return [
        Comment(
            id=comment_data["id"],
            body=comment_data["body"],
            source=comment_data.get("source", "johnny-johnny"),
            created_at=comment_data.get("created_at"),
            provider_metadata=comment_data.get("provider_metadata", {}),
        )
        for raw_comment_data in data.get("comments", []) or []
        for comment_data in [_mapping(raw_comment_data, "comment")]
    ]


def _list(data: Mapping[str, Any], key: str) -> list[str]:
    value = data.get(key)

    if value is None:
        return []

    return list(value)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"Backlog {name} must be a mapping.")
    return value
