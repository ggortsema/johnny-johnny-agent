from dataclasses import dataclass, field

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


@dataclass
class CreateEpicOperation:
    epic: Epic


@dataclass
class CreateIssueOperation:
    issue: Issue
    parent_epic: Epic


@dataclass
class AttachIssueOperation:
    issue: Issue
    parent_epic: Epic


BacklogOperation = CreateEpicOperation | CreateIssueOperation | AttachIssueOperation


@dataclass
class ExecutionPlan:
    operations: list[BacklogOperation] = field(default_factory=list)


def plan_reconcile_backlog(backlog: Backlog) -> ExecutionPlan:
    operations: list[BacklogOperation] = []

    for epic in backlog.epics:
        operations.append(CreateEpicOperation(epic=epic))

        for issue in epic.issues:
            operations.append(CreateIssueOperation(issue=issue, parent_epic=epic))
            operations.append(AttachIssueOperation(issue=issue, parent_epic=epic))

    return ExecutionPlan(operations=operations)