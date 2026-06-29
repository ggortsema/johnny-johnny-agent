from dataclasses import dataclass, field


@dataclass
class Issue:
    title: str
    repository: str
    description: str = ""


@dataclass
class Epic:
    title: str
    repository: str
    description: str = ""
    issues: list[Issue] = field(default_factory=list)


@dataclass
class Project:
    provider: str
    name: str


@dataclass
class Backlog:
    project: Project
    epics: list[Epic] = field(default_factory=list)