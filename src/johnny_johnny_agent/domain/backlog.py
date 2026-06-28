from dataclasses import dataclass, field


@dataclass
class Issue:
    title: str
    description: str = ""


@dataclass
class Epic:
    title: str
    description: str = ""
    issues: list[Issue] = field(default_factory=list)


@dataclass
class Backlog:
    epics: list[Epic] = field(default_factory=list)