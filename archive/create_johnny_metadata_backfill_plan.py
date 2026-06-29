import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path


SOURCE_FILE = Path("mycroftai-roadmap.json")
OUTPUT_FILE = Path("data/output/johnny-metadata-backfill-plan.json")
TARGET_OWNER = "ggortsema"
TARGET_REPO = "styxcd-docs"
TARGET_REPOSITORY = f"{TARGET_OWNER}/{TARGET_REPO}"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"^\[epic\]\s*", "", value)
    value = re.sub(r"^epic:\s*", "", value)
    value = re.sub(r"^issue:\s*", "", value)
    value = re.sub(r"`", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value


def clean_title(title: str) -> str:
    title = re.sub(r"^\[Epic\]\s*", "", title)
    title = re.sub(r"^Epic:\s*", "", title)
    title = re.sub(r"^Issue:\s*", "", title)
    return title.strip()


def github_rest(method: str, path: str, body: dict | None = None) -> dict | list:
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("Missing required environment variable: GITHUB_TOKEN")

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")

            if not response_body:
                return {}

            return json.loads(response_body)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(f"GitHub REST error {error.code}: {error_body}") from error


def list_sub_issues(issue_number: int) -> list[dict]:
    result = github_rest(
        "GET",
        f"/repos/{TARGET_OWNER}/{TARGET_REPO}/issues/{issue_number}/sub_issues",
    )

    if not isinstance(result, list):
        return []

    return result


def build_metadata_block(
        item_id: str,
        item_type: str,
        parent_id: str | None,
) -> str:
    lines = [
        "<!-- johnny-johnny",
        f"id: {item_id}",
        "schema: backlog-v1",
        f"type: {item_type}",
    ]

    if parent_id:
        lines.append(f"parent: {parent_id}")

    lines.append("-->")

    return "\n".join(lines)


def main() -> None:
    data = json.loads(SOURCE_FILE.read_text())
    items = data["items"]

    issue_items_by_number: dict[int, dict] = {}

    for item in items:
        content = item.get("content") or {}

        if content.get("repository") != TARGET_REPOSITORY:
            continue

        issue_items_by_number[content["number"]] = item

    print(f"Loaded {len(issue_items_by_number)} issues from {TARGET_REPOSITORY}")
    print("Reading sub-issue relationships from GitHub...")

    parent_by_child_number: dict[int, int] = {}
    sub_issue_numbers_by_parent_number: dict[int, list[int]] = {}

    for issue_number in sorted(issue_items_by_number):
        sub_issues = list_sub_issues(issue_number)
        sub_issue_numbers = [
            sub_issue["number"]
            for sub_issue in sub_issues
            if "number" in sub_issue
        ]

        if sub_issue_numbers:
            sub_issue_numbers_by_parent_number[issue_number] = sub_issue_numbers

            for child_number in sub_issue_numbers:
                parent_by_child_number[child_number] = issue_number

            print(f"- #{issue_number} has {len(sub_issue_numbers)} sub-issues")

    plan = []

    for issue_number in sorted(issue_items_by_number):
        item = issue_items_by_number[issue_number]
        content = item["content"]

        title = content["title"]
        body = content.get("body") or ""
        url = content["url"]

        item_id = slugify(clean_title(title))

        if issue_number in sub_issue_numbers_by_parent_number:
            item_type = "epic"
            parent_id = None
            warning = None
        else:
            item_type = "issue"
            parent_number = parent_by_child_number.get(issue_number)

            if parent_number:
                parent_item = issue_items_by_number[parent_number]
                parent_title = parent_item["content"]["title"]
                parent_id = slugify(clean_title(parent_title))
                warning = None
            else:
                parent_id = None
                warning = "No parent detected"

        metadata = build_metadata_block(
            item_id=item_id,
            item_type=item_type,
            parent_id=parent_id,
        )

        already_has_metadata = "<!-- johnny-johnny" in body

        plan.append(
            {
                "number": issue_number,
                "title": title,
                "url": url,
                "type": item_type,
                "id": item_id,
                "parent": parent_id,
                "already_has_metadata": already_has_metadata,
                "warning": warning,
                "metadata": metadata,
            }
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(plan, indent=2) + "\n")

    print()
    print(f"Wrote {OUTPUT_FILE}")
    print(f"Items planned: {len(plan)}")

    warnings = [item for item in plan if item["warning"]]
    print(f"Warnings: {len(warnings)}")

    print()
    print("Preview:")
    for item in plan[:20]:
        warning = f" warning={item['warning']}" if item["warning"] else ""
        print(
            f"- #{item['number']} {item['type']} "
            f"{item['id']} parent={item['parent']}{warning}"
        )


if __name__ == "__main__":
    main()