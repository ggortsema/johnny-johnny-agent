import re
from pathlib import Path
from typing import Any

import yaml

from johnny_johnny_agent.capabilities.github.client import (
    get_viewer_project_by_title,
    list_project_issues,
)


_METADATA_PATTERN = re.compile(
    r"<!--\s*johnny-johnny(?P<body>.*?)-->",
    re.DOTALL,
)


def generate_backlog_yaml_from_github_project(
        project_title: str,
        output_path: str,
) -> None:
    project = get_viewer_project_by_title(project_title)
    issues = list_project_issues(project["id"])

    backlog = github_pull_to_backlog_dict(
        {
            "project": project,
            "issues": issues,
        }
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        yaml.safe_dump(
            backlog,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )


def github_pull_to_backlog_dict(data: dict[str, Any]) -> dict[str, Any]:
    project = data["project"]
    rows = data.get("issues", [])

    epics_by_id: dict[str, dict[str, Any]] = {}
    child_rows: list[tuple[dict[str, Any], dict[str, str]]] = []

    epic_order = 1000

    for row in rows:
        metadata = _extract_johnny_metadata(row.get("body", ""))
        item_type = metadata.get("type")

        if item_type == "epic":
            epic = _work_item_from_row(
                row=row,
                metadata=metadata,
                item_type="epic",
                order=epic_order,
            )
            epic["title"] = _clean_epic_title(epic["title"])
            epic["issues"] = []
            epics_by_id[epic["id"]] = epic
            epic_order += 1000

        elif item_type == "issue":
            child_rows.append((row, metadata))

    child_order_by_parent: dict[str, int] = {}

    for row, metadata in child_rows:
        parent_id = metadata.get("parent")

        if not parent_id:
            continue

        if parent_id not in epics_by_id:
            epics_by_id[parent_id] = {
                "id": parent_id,
                "type": "epic",
                "title": f"[Missing Epic] {parent_id}",
                "repository": row.get("repository", ""),
                "status": _project_status(row),
                "issue_state": _issue_state(row),
                "order": epic_order,
                "description": "Generated placeholder because this issue referenced a parent epic not found in the pull.",
                "acceptance_criteria": [],
                "labels": [],
                "assignees": [],
                "milestone": None,
                "provider_metadata": {},
                "issues": [],
            }
            epic_order += 1000

        child_order_by_parent[parent_id] = child_order_by_parent.get(parent_id, 0) + 1000

        issue = _work_item_from_row(
            row=row,
            metadata=metadata,
            item_type="issue",
            order=child_order_by_parent[parent_id],
        )

        epics_by_id[parent_id]["issues"].append(issue)

    epics = sorted(epics_by_id.values(), key=lambda item: item["order"])

    for epic in epics:
        epic["issues"] = sorted(epic["issues"], key=lambda item: item["order"])

    return {
        "version": 1,
        "project": {
            "provider": "github",
            "title": project.get("title"),
            "number": project.get("number"),
            "url": project.get("url"),
            "provider_metadata": {
                "github": {
                    "project_id": project.get("id"),
                }
            },
        },
        "epics": epics,
    }


def _work_item_from_row(
        row: dict[str, Any],
        metadata: dict[str, str],
        item_type: str,
        order: int,
) -> dict[str, Any]:
    stable_id = metadata.get("id") or _slug(row["title"])

    return {
        "id": stable_id,
        "type": item_type,
        "title": row["title"],
        "repository": row.get("repository", ""),
        "status": _project_status(row),
        "issue_state": _issue_state(row),
        "order": order,
        "description": _clean_description(
            _strip_johnny_metadata(row.get("body", "")).strip()
        ),
        "acceptance_criteria": [],
        "labels": _names(row.get("labels", [])),
        "assignees": _names(row.get("assignees", [])),
        "milestone": _milestone(row.get("milestone")),
        "provider_metadata": {
            "github": {
                "issue_id": row.get("id"),
                "database_id": row.get("database_id"),
                "number": row.get("number"),
                "url": row.get("url"),
                "project_item_id": row.get("project_item_id"),
            }
        },
    }


def _project_status(row: dict[str, Any]) -> str:
    return (
            row.get("project_status")
            or row.get("status")
            or "Backlog"
    )


def _issue_state(row: dict[str, Any]) -> str:
    return row.get("state") or "OPEN"


def _extract_johnny_metadata(body: str) -> dict[str, str]:
    match = _METADATA_PATTERN.search(body or "")

    if not match:
        return {}

    result: dict[str, str] = {}

    for line in match.group("body").splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()

    return result


def _strip_johnny_metadata(body: str) -> str:
    return _METADATA_PATTERN.sub("", body or "").strip()


def _clean_description(description: str) -> str:
    description = description.strip()

    if description == "Description:":
        return ""

    if description.startswith("Description:\n\n"):
        return description.removeprefix("Description:\n\n").strip()

    if description.startswith("Description:\n"):
        return description.removeprefix("Description:\n").strip()

    return description


def _clean_epic_title(title: str) -> str:
    return title.removeprefix("[Epic] ").strip()


def _names(values: list[Any]) -> list[str]:
    names: list[str] = []

    for value in values or []:
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, dict):
            names.append(
                value.get("name")
                or value.get("login")
                or value.get("title")
                or str(value)
            )
        else:
            names.append(str(value))

    return names


def _milestone(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return value.get("title") or value.get("name")

    return str(value)


def _slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"^\[epic\]\s*", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")