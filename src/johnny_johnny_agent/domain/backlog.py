from dataclasses import dataclass, field
from typing import Any


ProviderMetadata = dict[str, Any]


@dataclass
class Issue:
    id: str
    type: str
    title: str
    repository: str
    status: str
    issue_state: str
    order: int
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    milestone: str | None = None
    provider_metadata: ProviderMetadata = field(default_factory=dict)


@dataclass
class Epic:
    id: str
    type: str
    title: str
    repository: str
    status: str
    issue_state: str
    order: int
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    milestone: str | None = None
    provider_metadata: ProviderMetadata = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)


@dataclass
class Project:
    provider: str
    title: str
    number: int | None = None
    url: str | None = None
    provider_metadata: ProviderMetadata = field(default_factory=dict)

    @property
    def name(self) -> str:
        """
        Temporary compatibility alias while older code still references
        project.name.
        """
        return self.title


@dataclass
class Backlog:
    project: Project
    epics: list[Epic] = field(default_factory=list)