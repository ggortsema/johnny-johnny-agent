import re

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


def parse_backlog(markdown: str) -> Backlog:
    epic_title = _extract_epic_title(markdown)
    epic_description = _extract_epic_description(markdown)
    issues = _extract_issues(markdown)

    epic = Epic(
        title=epic_title,
        description=epic_description,
        issues=issues,
    )

    return Backlog(epics=[epic])


def _extract_epic_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# Epic:"):
            return line.removeprefix("# Epic:").strip()

    raise ValueError("Epic title not found")


def _extract_epic_description(markdown: str) -> str:
    lines = markdown.splitlines()
    description_lines: list[str] = []
    in_goal_section = False

    for line in lines:
        if line.startswith("## "):
            in_goal_section = line.strip() == "## Goal"
            continue

        if in_goal_section and line.strip():
            description_lines.append(line.strip())

    return " ".join(description_lines)


def _extract_issues(markdown: str) -> list[Issue]:
    issue_pattern = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
    issues: list[Issue] = []

    for match in issue_pattern.finditer(markdown):
        issue_title = match.group(1).strip().strip("*").strip()
        issues.append(Issue(title=issue_title))

    return issues