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
        stripped_line = line.strip()

        if stripped_line.startswith("## "):
            if in_goal_section:
                break

            in_goal_section = stripped_line == "## Goal"
            continue

        if in_goal_section and stripped_line:
            description_lines.append(stripped_line)

    return "\n\n".join(description_lines)


def _extract_issues(markdown: str) -> list[Issue]:
    lines = markdown.splitlines()
    issues: list[Issue] = []

    current_title: str | None = None
    current_description_lines: list[str] = []

    issue_heading_pattern = re.compile(r"^\d+\.\s+(.+)$")

    def flush_current_issue() -> None:
        nonlocal current_title, current_description_lines

        if current_title is None:
            return

        issues.append(
            Issue(
                title=current_title,
                description="\n\n".join(current_description_lines).strip(),
            )
        )

        current_title = None
        current_description_lines = []

    for line in lines:
        stripped_line = line.strip()
        match = issue_heading_pattern.match(stripped_line)

        if match:
            flush_current_issue()
            current_title = match.group(1).strip().strip("*").strip()
            current_description_lines = []
            continue

        if current_title is not None:
            if stripped_line.startswith("#"):
                flush_current_issue()
                continue

            if stripped_line:
                current_description_lines.append(stripped_line)

    flush_current_issue()

    return issues