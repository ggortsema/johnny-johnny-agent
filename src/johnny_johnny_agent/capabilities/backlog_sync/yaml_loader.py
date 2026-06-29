from pathlib import Path

import yaml

from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue, Project


def load_backlog_yaml(backlog_path: str) -> Backlog:
    backlog_file = Path(backlog_path)

    if not backlog_file.exists():
        raise RuntimeError(f"Backlog YAML not found: {backlog_file}")

    data = yaml.safe_load(backlog_file.read_text(encoding="utf-8"))

    project_data = data["project"]

    epics = []
    for epic_data in data.get("epics", []):
        issues = [
            Issue(
                title=issue_data["name"],
                repository=issue_data["repository"],
                description=issue_data.get("description", ""),
            )
            for issue_data in epic_data.get("issues", [])
        ]

        epics.append(
            Epic(
                title=epic_data["name"],
                repository=epic_data["repository"],
                description=epic_data.get("description", ""),
                issues=issues,
            )
        )

    return Backlog(
        project=Project(
            provider=project_data["provider"],
            name=project_data["name"],
        ),
        epics=epics,
    )