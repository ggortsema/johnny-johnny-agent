import json
import os
import urllib.error
import urllib.request
from typing import Any


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def execute_graphql(query: str, variables: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("Missing required environment variable: GITHUB_TOKEN")

    payload = {
        "query": query,
        "variables": variables or {},
    }

    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
        result = json.loads(body)

    if "errors" in result:
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")

    return result["data"]


def list_viewer_projects() -> list[dict]:
    query = """
    query ListViewerProjects {
      viewer {
        login
        projectsV2(first: 20) {
          nodes {
            id
            number
            title
            url
          }
        }
      }
    }
    """

    data = execute_graphql(query)

    return data["viewer"]["projectsV2"]["nodes"]


def get_viewer_project_by_title(project_title: str) -> dict:
    projects = list_viewer_projects()

    for project in projects:
        if project["title"] == project_title:
            return project

    raise RuntimeError(f"GitHub project not found: {project_title}")


def get_repository(owner: str, name: str) -> dict:
    query = """
    query GetRepository($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        name
        nameWithOwner
        url
      }
    }
    """

    data = execute_graphql(
        query,
        {
            "owner": owner,
            "name": name,
        },
    )

    repository = data["repository"]

    if repository is None:
        raise RuntimeError(f"GitHub repository not found: {owner}/{name}")

    return repository


def list_project_issue_titles(project_id: str) -> set[str]:
    query = """
    query ListProjectIssues($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              content {
                ... on Issue {
                  title
                }
              }
            }
          }
        }
      }
    }
    """

    data = execute_graphql(query, {"projectId": project_id})

    items = data["node"]["items"]["nodes"]
    titles: set[str] = set()

    for item in items:
        content = item.get("content")
        if content and content.get("title"):
            titles.add(content["title"])

    return titles


def create_issue(repository_id: str, title: str, body: str = "") -> dict:
    mutation = """
    mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
      createIssue(input: {
        repositoryId: $repositoryId
        title: $title
        body: $body
      }) {
        issue {
          id
          databaseId
          number
          title
          url
        }
      }
    }
    """

    data = execute_graphql(
        mutation,
        {
            "repositoryId": repository_id,
            "title": title,
            "body": body,
        },
    )

    return data["createIssue"]["issue"]


def add_issue_to_project(project_id: str, issue_id: str) -> dict:
    mutation = """
    mutation AddIssueToProject($projectId: ID!, $issueId: ID!) {
      addProjectV2ItemById(input: {
        projectId: $projectId
        contentId: $issueId
      }) {
        item {
          id
        }
      }
    }
    """

    data = execute_graphql(
        mutation,
        {
            "projectId": project_id,
            "issueId": issue_id,
        },
    )

    return data["addProjectV2ItemById"]["item"]


def get_project_status_field(project_id: str) -> dict:
    query = """
    query GetProjectStatusField($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    data = execute_graphql(query, {"projectId": project_id})
    fields = data["node"]["fields"]["nodes"]

    for field in fields:
        if not field:
            continue

        if field.get("name") == "Status":
            return field

    raise RuntimeError("GitHub Project Status field not found.")


def update_project_item_status(
        project_id: str,
        project_item_id: str,
        status: str,
) -> dict:
    status_field = get_project_status_field(project_id)
    option = _find_single_select_option(
        field=status_field,
        option_name=status,
    )

    mutation = """
    mutation UpdateProjectItemStatus(
      $projectId: ID!
      $itemId: ID!
      $fieldId: ID!
      $optionId: String!
    ) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: {
          singleSelectOptionId: $optionId
        }
      }) {
        projectV2Item {
          id
        }
      }
    }
    """

    data = execute_graphql(
        mutation,
        {
            "projectId": project_id,
            "itemId": project_item_id,
            "fieldId": status_field["id"],
            "optionId": option["id"],
        },
    )

    return data["updateProjectV2ItemFieldValue"]["projectV2Item"]


def _find_single_select_option(
        field: dict[str, Any],
        option_name: str,
) -> dict[str, Any]:
    for option in field.get("options", []):
        if option["name"] == option_name:
            return option

    valid_options = [
        option["name"]
        for option in field.get("options", [])
    ]

    raise RuntimeError(
        f"Invalid Status value: {option_name}. "
        f"Valid values: {', '.join(valid_options)}"
    )


def execute_rest(
        method: str,
        path: str,
        body: dict | None = None,
) -> dict:
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("Missing required environment variable: GITHUB_TOKEN")

    url = f"https://api.github.com{path}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url,
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


def add_sub_issue(
        owner: str,
        repo: str,
        parent_issue_number: int,
        child_issue_database_id: int,
) -> dict:
    return execute_rest(
        method="POST",
        path=f"/repos/{owner}/{repo}/issues/{parent_issue_number}/sub_issues",
        body={
            "sub_issue_id": child_issue_database_id,
        },
    )


def list_project_issues(project_id: str) -> list[dict]:
    query = """
query ListProjectIssues($projectId: ID!, $after: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          fieldValues(first: 50) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                optionId
                field {
                  ... on ProjectV2SingleSelectField {
                    name
                  }
                }
              }
            }
          }
          content {
            ... on Issue {
              id
              databaseId
              number
              title
              body
              url
              state
              createdAt
              updatedAt
              repository {
                nameWithOwner
              }
              labels(first: 50) {
                nodes {
                  name
                }
              }
              assignees(first: 50) {
                nodes {
                  login
                }
              }
              milestone {
                title
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
        nodes = items["nodes"]

        for item in nodes:
            content = item.get("content")

            if not content:
                continue

            if not content.get("title"):
                continue

            project_status = _project_status_from_item(item)

            issues.append(
                {
                    "project_item_id": item["id"],
                    "project_status": project_status,
                    "id": content["id"],
                    "database_id": content["databaseId"],
                    "number": content["number"],
                    "title": content["title"],
                    "body": content.get("body") or "",
                    "url": content["url"],
                    "state": content["state"],
                    "created_at": content["createdAt"],
                    "updated_at": content["updatedAt"],
                    "repository": content["repository"]["nameWithOwner"],
                    "labels": [
                        label["name"]
                        for label in content["labels"]["nodes"]
                    ],
                    "assignees": [
                        assignee["login"]
                        for assignee in content["assignees"]["nodes"]
                    ],
                    "milestone": (
                        content["milestone"]["title"]
                        if content.get("milestone")
                        else None
                    ),
                }
            )

        page_info = items["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        after = page_info["endCursor"]

    return issues


def _project_status_from_item(item: dict[str, Any]) -> str | None:
    field_values = item.get("fieldValues", {}).get("nodes", [])

    for field_value in field_values:
        if not field_value:
            continue

        field = field_value.get("field") or {}

        if field.get("name") == "Status":
            return field_value.get("name")

    return None


def delete_issue(issue_id: str) -> None:
    mutation = """
    mutation DeleteIssue($issueId: ID!) {
      deleteIssue(input: {issueId: $issueId}) {
        clientMutationId
      }
    }
    """

    execute_graphql(mutation, {"issueId": issue_id})