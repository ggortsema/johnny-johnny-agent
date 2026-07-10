#!/usr/bin/env python3
"""Historical prototype for exporting PostgreSQL backlog data to YAML.

The supported runtime interface is now `jj backlog db export`. This script is
retained as design history and should not be treated as the primary workflow.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from psycopg import connect
from psycopg.rows import dict_row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export PostgreSQL backlog data to backlog.yml.")
    parser.add_argument("output_path", help="Path to write exported backlog YAML")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection string. Defaults to DATABASE_URL.",
    )
    parser.add_argument("--provider", default="github")
    parser.add_argument("--provider-account-username", default="ggortsema")
    parser.add_argument("--provider-project-title", default="MycroftAI Engineering Roadmap")
    args = parser.parse_args()

    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")

    return args


def main() -> None:
    args = parse_args()

    with connect(args.database_url, row_factory=dict_row) as conn:
        project = fetch_provider_project(
            conn,
            provider=args.provider,
            username=args.provider_account_username,
            title=args.provider_project_title,
        )
        if not project:
            raise RuntimeError(
                "Provider project not found: "
                f"{args.provider} / {args.provider_account_username} / {args.provider_project_title}"
            )

        epics = fetch_items(conn, provider_project_id=project["id"], parent_item_id=None)
        epic_documents = []
        for epic in epics:
            epic_doc = item_to_yaml_dict(conn, epic)
            issues = fetch_items(conn, provider_project_id=project["id"], parent_item_id=epic["id"])
            epic_doc["issues"] = [item_to_yaml_dict(conn, issue) for issue in issues]
            epic_documents.append(epic_doc)

    document = {
        "version": 1,
        "project": {
            "provider": args.provider,
            "title": project["title"],
            "number": project["external_number"],
            "url": project["url"],
            "provider_metadata": normalize_json(project["provider_metadata"]),
        },
        "epics": epic_documents,
    }

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(
            normalize_json(document),
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )
    print(f"Exported backlog YAML to {output_path}")


def fetch_provider_project(conn, *, provider: str, username: str, title: str):
    return conn.execute(
        """
        SELECT pp.*
        FROM provider_projects pp
        JOIN provider_accounts pa ON pa.id = pp.provider_account_id
        JOIN providers p ON p.id = pa.provider_id
        WHERE p.key = %s
          AND lower(pa.username) = lower(%s)
          AND lower(pp.title) = lower(%s)
          AND pp.deleted_at IS NULL
          AND pa.deleted_at IS NULL
          AND p.deleted_at IS NULL
        """,
        (provider, username, title),
    ).fetchone()


def fetch_items(conn, *, provider_project_id, parent_item_id):
    if parent_item_id is None:
        return conn.execute(
            """
            SELECT *
            FROM backlog_items
            WHERE provider_project_id = %s
              AND parent_item_id IS NULL
              AND deleted_at IS NULL
            ORDER BY item_order, canonical_id
            """,
            (provider_project_id,),
        ).fetchall()

    return conn.execute(
        """
        SELECT *
        FROM backlog_items
        WHERE provider_project_id = %s
          AND parent_item_id = %s
          AND deleted_at IS NULL
        ORDER BY item_order, canonical_id
        """,
        (provider_project_id, parent_item_id),
    ).fetchall()


def item_to_yaml_dict(conn, item) -> dict[str, Any]:
    return {
        "id": item["canonical_id"],
        "type": item["item_type"],
        "title": item["title"],
        "repository": item["repository"],
        "status": item["status"],
        "issue_state": item["issue_state"],
        "order": item["item_order"],
        "description": item["description"],
        "acceptance_criteria": fetch_acceptance_criteria(conn, item["id"]),
        "comments": fetch_comments(conn, item["id"]),
        "labels": fetch_labels(conn, item["id"]),
        "assignees": fetch_assignees(conn, item["id"]),
        "milestone": item["milestone"],
        "provider_metadata": normalize_json(item["provider_metadata"]),
    }


def fetch_acceptance_criteria(conn, backlog_item_id) -> list[str]:
    rows = conn.execute(
        """
        SELECT body
        FROM backlog_item_acceptance_criteria
        WHERE backlog_item_id = %s
          AND deleted_at IS NULL
        ORDER BY position
        """,
        (backlog_item_id,),
    ).fetchall()
    return [row["body"] for row in rows]


def fetch_comments(conn, backlog_item_id) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT canonical_comment_id, body, source, created_at, provider_metadata
        FROM backlog_item_comments
        WHERE backlog_item_id = %s
          AND deleted_at IS NULL
        ORDER BY position
        """,
        (backlog_item_id,),
    ).fetchall()
    return [
        {
            "id": row["canonical_comment_id"],
            "body": row["body"],
            "source": row["source"],
            "created_at": row["created_at"],
            "provider_metadata": normalize_json(row["provider_metadata"]),
        }
        for row in rows
    ]


def fetch_labels(conn, backlog_item_id) -> list[str]:
    rows = conn.execute(
        """
        SELECT label
        FROM backlog_item_labels
        WHERE backlog_item_id = %s
        ORDER BY label
        """,
        (backlog_item_id,),
    ).fetchall()
    return [row["label"] for row in rows]


def fetch_assignees(conn, backlog_item_id) -> list[str]:
    rows = conn.execute(
        """
        SELECT assignee
        FROM backlog_item_assignees
        WHERE backlog_item_id = %s
        ORDER BY assignee
        """,
        (backlog_item_id,),
    ).fetchall()
    return [row["assignee"] for row in rows]


def normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_json(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [normalize_json(inner) for inner in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
