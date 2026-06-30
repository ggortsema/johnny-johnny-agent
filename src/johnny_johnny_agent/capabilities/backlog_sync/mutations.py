from johnny_johnny_agent.domain.backlog import Backlog, Issue


def update_issue_status(
        backlog: Backlog,
        issue_id: str,
        status: str,
) -> Issue:
    issue = find_issue(backlog, issue_id)
    issue.status = status
    return issue


def find_issue(
        backlog: Backlog,
        issue_id: str,
) -> Issue:
    for epic in backlog.epics:
        for issue in epic.issues:
            if issue.id == issue_id:
                return issue

    raise RuntimeError(f"Issue not found: {issue_id}")