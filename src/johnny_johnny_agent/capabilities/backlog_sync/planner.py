from dataclasses import dataclass, field
from typing import Any

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


@dataclass
class CreateEpicOperation:
    epic: Epic


@dataclass
class CreateIssueOperation:
    issue: Issue
    parent_epic: Epic


@dataclass
class AddIssueToProjectOperation:
    issue: Issue


@dataclass
class AttachIssueToEpicOperation:
    issue: Issue
    parent_epic: Epic


BacklogOperation = (
        CreateEpicOperation
        | CreateIssueOperation
        | AddIssueToProjectOperation
        | AttachIssueToEpicOperation
)


@dataclass
class ExecutionPlan:
    operations: list[BacklogOperation] = field(default_factory=list)


def plan_reconcile_backlog(
        backlog: Backlog,
        current_project_issues: list[dict[str, Any]],
) -> ExecutionPlan:
    operations: list[BacklogOperation] = []

    live_by_jj_id = _index_live_items_by_jj_id(current_project_issues)

    for epic in backlog.epics:
        live_epic = live_by_jj_id.get(epic.id)

        if live_epic is None:
            operations.append(CreateEpicOperation(epic=epic))

        for issue in epic.issues:
            live_issue = live_by_jj_id.get(issue.id)

            if live_issue is None:
                operations.append(CreateIssueOperation(issue=issue, parent_epic=epic))
                operations.append(AddIssueToProjectOperation(issue=issue))
                operations.append(
                    AttachIssueToEpicOperation(
                        issue=issue,
                        parent_epic=epic,
                    )
                )

    return ExecutionPlan(operations=operations)


def _index_live_items_by_jj_id(
        current_project_issues: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for row in current_project_issues:
        metadata = _extract_johnny_metadata(row.get("body", ""))

        jj_id = metadata.get("id")

        if jj_id:
            result[jj_id] = row

    return result


def _extract_johnny_metadata(body: str) -> dict[str, str]:
    start = body.find("<!-- johnny-johnny")

    if start == -1:
        return {}

    end = body.find("-->", start)

    if end == -1:
        return {}

    block = body[start:end]

    result: dict[str, str] = {}

    for line in block.splitlines():
        line = line.strip()

        if not line or line.startswith("<!--"):
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()

    return result