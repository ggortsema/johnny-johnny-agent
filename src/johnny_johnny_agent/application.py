from pathlib import Path

from johnny_johnny_agent.capabilities.backlog_sync import loader
from johnny_johnny_agent.capabilities.backlog_sync.parser import markdown


def start(backlog_path: str | Path = "data/input/backlog/Backlog-as-Code-Synchronization-Epic.md") -> None:
    print("Johnny-Johnny Agent")
    print()
    print("Loading backlog...")

    backlog_markdown = loader.load_markdown(backlog_path)
    backlog = markdown.parse_backlog(backlog_markdown)

    print(f"Loaded backlog markdown: {len(backlog_markdown)} characters")
    print()

    print(f"Epics found: {len(backlog.epics)}")

    for epic in backlog.epics:
        print()
        print(f"Epic: {epic.title}")
        print(f"Description: {epic.description}")
        print(f"Issues found: {len(epic.issues)}")

        for issue in epic.issues:
            print(f"- {issue.title}")

    print()
    print("Done.")


if __name__ == "__main__":
    start()