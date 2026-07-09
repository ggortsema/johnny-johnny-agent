#!/usr/bin/env python3
"""Import a backlog.yml file into the canonical PostgreSQL backlog schema.

Draft script for design-canonical-backlog-persistence.
Do not run until the schema and mapping have been reviewed.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml
from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import backlog.yml into PostgreSQL.")
    parser.add_argument("backlog_path", help="Path to backlog.yml")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection string. Defaults to DATABASE_URL.",
    )
    parser.add_argument("--user-display-name", default="Grant Gortsema")
    parser.add_argument("--user-primary-email", default=None)
    parser.add_argument("--provider-account-username", default="ggortsema")
    parser.add_argument("--provider-account-display-name", default="Grant Gortsema")
    parser.add_argument(
        "--replace-project-items",
        action="store_true",
        help="Delete existing backlog items for the provider project before importing.",
    )
    args = parser.parse_args()

    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")

    return args


def main() -> None:
    args = parse_args()
    backlog_path = Path(args.backlog_path)
    data = yaml.safe_load(backlog_path.read_text(encoding="utf-8")) or {}

    project_data = data["project"]
    provider_key = project_data["provider"]
    provider_metadata = project_data.get("provider_metadata", {}) or {}
    provider_specific_metadata = provider_metadata.get(provider_key, {}) or {}

    with connect(args.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            user_id = upsert_user(
                conn,
                display_name=args.user_display_name,
                primary_email=args.user_primary_email,
            )
            provider_id = upsert_provider(conn, key=provider_key)
            provider_account_id = upsert_provider_account(
                conn,
                user_id=user_id,
                provider_id=provider_id,
                username=args.provider_account_username,
                display_name=args.provider_account_display_name,
            )
            provider_project_id = upsert_provider_project(
                conn,
                provider_account_id=provider_account_id,
                title=project_data["title"],
                external_id=provider_specific_metadata.get("project_id"),
                external_number=project_data.get("number"),
                url=project_data.get("url"),
                provider_metadata=provider_metadata,
            )

            if args.replace_project_items:
                conn.execute(
                    "DELETE FROM backlog_items WHERE provider_project_id = %s",
                    (provider_project_id,),
                )

            item_id_by_canonical_id: dict[str, Any] = {}

            for epic_data in data.get("epics", []) or []:
                epic_id = upsert_backlog_item(
                    conn,
                    provider_project_id=provider_project_id,
                    parent_item_id=None,
                    item_data=epic_data,
                    provider_key=provider_key,
                )
                item_id_by_canonical_id[epic_data["id"]] = epic_id
                replace_item_children(conn, epic_id, epic_data)

                for issue_data in epic_data.get("issues", []) or []:
                    issue_id = upsert_backlog_item(
                        conn,
                        provider_project_id=provider_project_id,
                        parent_item_id=epic_id,
                        item_data=issue_data,
                        provider_key=provider_key,
                    )
                    item_id_by_canonical_id[issue_data["id"]] = issue_id
                    replace_item_children(conn, issue_id, issue_data)

    print(
        "Imported backlog into PostgreSQL: "
        f"{provider_key} / {args.provider_account_username} / {project_data['title']}"
    )


def upsert_user(conn, *, display_name: str, primary_email: str | None):
    if primary_email:
        return conn.execute(
            """
            INSERT INTO users (display_name, primary_email)
            VALUES (%s, %s)
            ON CONFLICT (lower(primary_email)) WHERE primary_email IS NOT NULL AND deleted_at IS NULL
            DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (display_name, primary_email),
        ).fetchone()["id"]

    # If no email is supplied, there is no unique key to conflict on. Reuse by display_name.
    row = conn.execute(
        "SELECT id FROM users WHERE display_name = %s AND deleted_at IS NULL ORDER BY created_at LIMIT 1",
        (display_name,),
    ).fetchone()
    if row:
        return row["id"]

    return conn.execute(
        "INSERT INTO users (display_name, primary_email) VALUES (%s, NULL) RETURNING id",
        (display_name,),
    ).fetchone()["id"]


def upsert_provider(conn, *, key: str):
    display_name = {
        "github": "GitHub",
        "jira": "Jira",
        "linear": "Linear",
        "gitlab": "GitLab",
        "local": "Local",
    }.get(key, key)

    return conn.execute(
        """
        INSERT INTO providers (key, display_name, enabled)
        VALUES (%s, %s, true)
        ON CONFLICT (key)
        DO UPDATE SET display_name = EXCLUDED.display_name, enabled = true
        RETURNING id
        """,
        (key, display_name),
    ).fetchone()["id"]


def upsert_provider_account(conn, *, user_id, provider_id, username: str, display_name: str | None):
    return conn.execute(
        """
        INSERT INTO provider_accounts (user_id, provider_id, username, display_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (provider_id, lower(username)) WHERE deleted_at IS NULL
        DO UPDATE SET user_id = EXCLUDED.user_id, display_name = EXCLUDED.display_name
        RETURNING id
        """,
        (user_id, provider_id, username, display_name),
    ).fetchone()["id"]


def upsert_provider_project(
    conn,
    *,
    provider_account_id,
    title: str,
    external_id: str | None,
    external_number: int | None,
    url: str | None,
    provider_metadata: dict[str, Any],
):
    return conn.execute(
        """
        INSERT INTO provider_projects (
            provider_account_id,
            external_id,
            external_number,
            title,
            url,
            provider_metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (provider_account_id, lower(title)) WHERE deleted_at IS NULL
        DO UPDATE SET
            external_id = EXCLUDED.external_id,
            external_number = EXCLUDED.external_number,
            url = EXCLUDED.url,
            provider_metadata = EXCLUDED.provider_metadata
        RETURNING id
        """,
        (provider_account_id, external_id, external_number, title, url, Jsonb(provider_metadata)),
    ).fetchone()["id"]


def upsert_backlog_item(
    conn,
    *,
    provider_project_id,
    parent_item_id,
    item_data: dict[str, Any],
    provider_key: str,
):
    provider_metadata = item_data.get("provider_metadata", {}) or {}
    provider_specific_metadata = provider_metadata.get(provider_key, {}) or {}

    return conn.execute(
        """
        INSERT INTO backlog_items (
            provider_project_id,
            parent_item_id,
            canonical_id,
            item_type,
            title,
            description,
            repository,
            status,
            issue_state,
            item_order,
            milestone,
            external_id,
            external_database_id,
            external_number,
            external_url,
            external_project_item_id,
            provider_metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (provider_project_id, canonical_id)
        DO UPDATE SET
            parent_item_id = EXCLUDED.parent_item_id,
            item_type = EXCLUDED.item_type,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            repository = EXCLUDED.repository,
            status = EXCLUDED.status,
            issue_state = EXCLUDED.issue_state,
            item_order = EXCLUDED.item_order,
            milestone = EXCLUDED.milestone,
            external_id = EXCLUDED.external_id,
            external_database_id = EXCLUDED.external_database_id,
            external_number = EXCLUDED.external_number,
            external_url = EXCLUDED.external_url,
            external_project_item_id = EXCLUDED.external_project_item_id,
            provider_metadata = EXCLUDED.provider_metadata
        RETURNING id
        """,
        (
            provider_project_id,
            parent_item_id,
            item_data["id"],
            item_data["type"],
            item_data["title"],
            item_data.get("description", ""),
            item_data["repository"],
            item_data["status"],
            item_data["issue_state"],
            item_data["order"],
            item_data.get("milestone"),
            provider_specific_metadata.get("issue_id"),
            provider_specific_metadata.get("database_id"),
            provider_specific_metadata.get("number"),
            provider_specific_metadata.get("url"),
            provider_specific_metadata.get("project_item_id"),
            Jsonb(provider_metadata),
        ),
    ).fetchone()["id"]


def replace_item_children(conn, backlog_item_id, item_data: dict[str, Any]) -> None:
    conn.execute("DELETE FROM backlog_item_acceptance_criteria WHERE backlog_item_id = %s", (backlog_item_id,))
    conn.execute("DELETE FROM backlog_item_comments WHERE backlog_item_id = %s", (backlog_item_id,))
    conn.execute("DELETE FROM backlog_item_labels WHERE backlog_item_id = %s", (backlog_item_id,))
    conn.execute("DELETE FROM backlog_item_assignees WHERE backlog_item_id = %s", (backlog_item_id,))

    for position, body in enumerate(item_data.get("acceptance_criteria", []) or [], start=1):
        conn.execute(
            """
            INSERT INTO backlog_item_acceptance_criteria (backlog_item_id, position, body, checked)
            VALUES (%s, %s, %s, false)
            """,
            (backlog_item_id, position, body),
        )

    for position, comment in enumerate(item_data.get("comments", []) or [], start=1):
        conn.execute(
            """
            INSERT INTO backlog_item_comments (
                backlog_item_id,
                canonical_comment_id,
                position,
                body,
                source,
                created_at,
                provider_metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                backlog_item_id,
                comment["id"],
                position,
                comment["body"],
                comment.get("source", "johnny-johnny"),
                comment.get("created_at"),
                Jsonb(comment.get("provider_metadata", {}) or {}),
            ),
        )

    for label in item_data.get("labels", []) or []:
        conn.execute(
            "INSERT INTO backlog_item_labels (backlog_item_id, label) VALUES (%s, %s)",
            (backlog_item_id, label),
        )

    for assignee in item_data.get("assignees", []) or []:
        conn.execute(
            "INSERT INTO backlog_item_assignees (backlog_item_id, assignee) VALUES (%s, %s)",
            (backlog_item_id, assignee),
        )


if __name__ == "__main__":
    main()
