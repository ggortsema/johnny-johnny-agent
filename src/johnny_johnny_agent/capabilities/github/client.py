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


def get_issue(issue_id: str) -> dict:
    query = """
    query GetIssue($issueId: ID!) {
      node(id: $issueId) {
        ... on Issue {
          id
          databaseId
          number
          title
          body
          url
          repository {
            nameWithOwner
          }
        }
      }
    }
    """

    data = execute_graphql(query, {"issueId": issue_id})
    issue = data.get("node")
    if not issue:
        raise RuntimeError(f"GitHub issue not found: {issue_id}")
    return issue


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
          body
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

    create_issue_result = data.get("createIssue")
    if not create_issue_result:
        raise RuntimeError(
            f"GitHub createIssue returned no createIssue payload for title: {title}"
        )

    issue = create_issue_result.get("issue")
    if not issue:
        raise RuntimeError(
            f"GitHub createIssue returned no issue payload for title: {title}. "
            f"Response payload: {create_issue_result}"
        )

    return issue


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


def delete_project_item(project_id: str, project_item_id: str) -> None:
    mutation = """
    mutation DeleteProjectItem($projectId: ID!, $projectItemId: ID!) {
      deleteProjectV2Item(input: {
        projectId: $projectId
        itemId: $projectItemId
      }) {
        deletedItemId
      }
    }
    """

    execute_graphql(
        mutation,
        {
            "projectId": project_id,
            "projectItemId": project_item_id,
        },
    )


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
        option_name=_canonical_status_to_github(status),
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


def clear_project_item_status(
        project_id: str,
        project_item_id: str,
) -> None:
    status_field = get_project_status_field(project_id)
    mutation = """
    mutation ClearProjectItemStatus(
      $projectId: ID!
      $itemId: ID!
      $fieldId: ID!
    ) {
      clearProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
      }) {
        projectV2Item {
          id
        }
      }
    }
    """
    execute_graphql(
        mutation,
        {
            "projectId": project_id,
            "itemId": project_item_id,
            "fieldId": status_field["id"],
        },
    )


def _canonical_status_to_github(status: str) -> str:
    status_by_canonical = {
        "Backlog": "Backlog",
        "Ready": "Ready",
        "In Progress": "In progress",
        "In Review": "In review",
        "Done": "Done",
    }

    return status_by_canonical.get(status, status)


def _github_status_to_canonical(status: str | None) -> str | None:
    if status is None:
        return None

    status_by_github = {
        "Backlog": "Backlog",
        "Ready": "Ready",
        "In progress": "In Progress",
        "In review": "In Review",
        "Done": "Done",
    }

    return status_by_github.get(status, status)


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
        *,
        replace_parent: bool = False,
) -> dict:
    return execute_rest(
        method="POST",
        path=f"/repos/{owner}/{repo}/issues/{parent_issue_number}/sub_issues",
        body={
            "sub_issue_id": child_issue_database_id,
            "replace_parent": replace_parent,
        },
    )


def remove_sub_issue(
        owner: str,
        repo: str,
        parent_issue_number: int,
        child_issue_database_id: int,
) -> dict:
    return execute_rest(
        method="DELETE",
        path=f"/repos/{owner}/{repo}/issues/{parent_issue_number}/sub_issue",
        body={
            "sub_issue_id": child_issue_database_id,
        },
    )


def get_issue_parent(issue_id: str) -> dict | None:
    query = """
    query GetIssueParent($issueId: ID!) {
      node(id: $issueId) {
        ... on Issue {
          parent {
            id
            databaseId
            number
            url
            repository {
              nameWithOwner
            }
          }
        }
      }
    }
    """

    data = execute_graphql(query, {"issueId": issue_id})
    node = data.get("node")
    if not node:
        raise RuntimeError(f"GitHub issue not found: {issue_id}")
    return node.get("parent")


def update_issue(
        issue_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
) -> dict:
    mutation = """
    mutation UpdateIssue($input: UpdateIssueInput!) {
      updateIssue(input: $input) {
        issue {
          id
          databaseId
          number
          title
          body
          url
        }
      }
    }
    """

    input_value: dict[str, Any] = {"id": issue_id}
    if title is not None:
        input_value["title"] = title
    if body is not None:
        input_value["body"] = body

    data = execute_graphql(mutation, {"input": input_value})
    result = data.get("updateIssue") or {}
    issue = result.get("issue")
    if not issue:
        raise RuntimeError(
            f"GitHub updateIssue returned no issue payload for: {issue_id}"
        )
    return issue


def delete_issue_comment(comment_id: str) -> None:
    mutation = """
    mutation DeleteIssueComment($commentId: ID!) {
      deleteIssueComment(input: {id: $commentId}) {
        clientMutationId
      }
    }
    """
    execute_graphql(mutation, {"commentId": comment_id})


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
              comments(first: 100) {
                nodes {
                  id
                  databaseId
                  body
                  url
                  createdAt
                  updatedAt
                }
              }
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
                    "comments": [
                        {
                            "id": comment["id"],
                            "database_id": comment["databaseId"],
                            "body": comment.get("body") or "",
                            "url": comment["url"],
                            "created_at": comment["createdAt"],
                            "updated_at": comment["updatedAt"],
                        }
                        for comment in content["comments"]["nodes"]
                    ],
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

def create_issue_comment(
        issue_id: str,
        body: str,
) -> dict:
    mutation = """
    mutation CreateIssueComment($issueId: ID!, $body: String!) {
      addComment(input: {
        subjectId: $issueId
        body: $body
      }) {
        commentEdge {
          node {
            id
            databaseId
            body
            url
            createdAt
            updatedAt
          }
        }
      }
    }
    """

    data = execute_graphql(
        mutation,
        {
            "issueId": issue_id,
            "body": body,
        },
    )

    return data["addComment"]["commentEdge"]["node"]

def _project_status_from_item(item: dict[str, Any]) -> str | None:
    field_values = item.get("fieldValues", {}).get("nodes", [])

    for field_value in field_values:
        if not field_value:
            continue

        field = field_value.get("field") or {}

        if field.get("name") == "Status":
            return _github_status_to_canonical(field_value.get("name"))

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