import re


def extract_epic_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# Epic:"):
            return line.removeprefix("# Epic:").strip()

    raise ValueError("Epic title not found")


def count_stories(markdown: str) -> int:
    story_pattern = re.compile(r"^\d+\.\s+.+", re.MULTILINE)
    return len(story_pattern.findall(markdown))