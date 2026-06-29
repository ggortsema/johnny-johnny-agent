import json
import os
import urllib.request

OWNER = "ggortsema"
REPOSITORY = "styxcd-docs"
PROJECT_TITLE = "MycroftAI Engineering Roadmap"

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def execute_graphql(query: str, variables: dict | None = None) -> dict:
    token = os.environ["GITHUB_TOKEN"]

    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=json.dumps(
            {
                "query": query,
                "variables": variables or {},
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


def get_project_id(project_title: str) -> str:
    query = """
    query {
      viewer {
        projectsV2(first: 20) {
          nodes {
            id
            title
          }
        }
      }
    }
    """

    data = execute_graphql(query)

    for project in data["viewer"]["projectsV2"]["nodes"]:
        if project["title"] == project_title:
            return project["id"]

    raise RuntimeError(f"Project not found: {project_title}")


def list_project_items(project_id: str) -> list[dict]:
    query = """
    query($projectId: ID!, $after: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              content {
                ... on Issue {
                  id
                  number
                  title
                  repository {
                    nameWithOwner
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    issues: list[dict] = []
    after: str | None = None

    while True:
        data = execute_graphql(
            query,
            {
                "projectId": project_id,
                "after": after,
            },
        )

        items = data["node"]["items"]

        for node in items["nodes"]:
            content = node.get("content")

            if not content:
                continue

            repository = content.get("repository") or {}
            if repository.get("nameWithOwner") != f"{OWNER}/{REPOSITORY}":
                continue

            issues.append(
                {
                    "id": content["id"],
                    "number": content["number"],
                    "title": content["title"],
                }
            )

        page_info = items["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        after = page_info["endCursor"]

    return issues


def delete_issue(issue_id: str) -> None:
    mutation = """
    mutation($issueId: ID!) {
      deleteIssue(input: {issueId: $issueId}) {
        clientMutationId
      }
    }
    """

    execute_graphql(mutation, {"issueId": issue_id})


def main() -> None:
    project_id = get_project_id(PROJECT_TITLE)
    issues = list_project_items(project_id)

    print(f"Found {len(issues)} issues in {OWNER}/{REPOSITORY}")
    print()

    confirm = input(
        f"This will permanently delete every listed issue from "
        f"{OWNER}/{REPOSITORY}. Type DELETE to continue: "
    )

    if confirm != "DELETE":
        print("Cancelled.")
        return

    for issue in reversed(issues):
        print(f"Deleting #{issue['number']} {issue['title']}")
        delete_issue(issue["id"])

    print()
    print("Done.")


if __name__ == "__main__":
    main()