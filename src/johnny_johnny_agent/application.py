from pathlib import Path

from johnny_johnny_agent.capabilities.backlog_sync import loader
from johnny_johnny_agent.capabilities.backlog_sync import parser


def start(backlog_path: str | Path = "data/input/backlog/Backlog-as-Code-Synchronization-Epic.md") -> None:
    print("Johnny-Johnny Agent")
    print()
    print("Loading backlog...")

    backlog_markdown = loader.load_markdown(backlog_path)

    print(f"Loaded backlog markdown: {len(backlog_markdown)} characters")
    print("Done.")

    epic_title = parser.extract_epic_title(backlog_markdown)
    print(f"Epic title:  {epic_title}")

    num_of_stories = parser.count_stories(backlog_markdown)
    print(f"Number of stories: {num_of_stories}")


if __name__ == "__main__":
    start()