"""PostgreSQL adapter for the canonical backlog domain model.

The adapter deliberately treats the database connection method as an
infrastructure concern. ``DATABASE_URL`` may point at a directly reachable
PostgreSQL server, a local SSH-tunnel endpoint, or a private AWS endpoint; the
persistence capability behaves the same in every case.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterator, Mapping, Protocol, Sequence

from johnny_johnny_agent.domain.backlog import Backlog, Comment, Epic, Issue, Project


DATABASE_SCHEMA = "johnny_johnny"
EXPECTED_TABLES = (
    "backlog_item_acceptance_criteria",
    "backlog_item_assignees",
    "backlog_item_comments",
    "backlog_item_labels",
    "backlog_items",
    "provider_accounts",
    "provider_projects",
    "providers",
    "users",
)

_PROVIDER_DISPLAY_NAMES = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "jira": "Jira",
    "linear": "Linear",
    "local": "Local",
}


class ConnectionLike(Protocol):
    """The small connection surface used by this adapter and its tests."""

    def __enter__(self) -> "ConnectionLike": ...

    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...

    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...


ConnectionFactory = Callable[[str], ConnectionLike]


class BacklogPersistenceError(RuntimeError):
    """Base error for PostgreSQL canonical backlog persistence."""


class ProviderProjectNotFoundError(BacklogPersistenceError):
    """Raised when an export target cannot be found."""


class RoundTripValidationError(BacklogPersistenceError):
    """Raised when a snapshot differs after writing and reading it back."""


@dataclass(frozen=True)
class BacklogLocation:
    """Stable lookup identity for a persisted provider project backlog."""

    provider: str
    provider_account_username: str
    project_title: str

    def describe(self) -> str:
        return (
            f"{self.provider} / {self.provider_account_username} / "
            f"{self.project_title}"
        )


@dataclass(frozen=True)
class DatabaseStatus:
    """Connection and canonical schema readiness details."""

    database: str
    database_user: str
    schema: str
    server_version: str
    available_tables: tuple[str, ...]
    missing_tables: tuple[str, ...]
    provider_count: int

    @property
    def expected_table_count(self) -> int:
        return len(EXPECTED_TABLES)

    @property
    def present_expected_table_count(self) -> int:
        return self.expected_table_count - len(self.missing_tables)

    @property
    def ready(self) -> bool:
        return not self.missing_tables and self.provider_count > 0


@dataclass(frozen=True)
class BacklogImportResult:
    """Summary of one committed snapshot replacement."""

    location: BacklogLocation
    provider_project_id: Any
    epic_count: int
    issue_count: int
    acceptance_criterion_count: int
    comment_count: int
    label_count: int
    assignee_count: int
    verified: bool


@dataclass(frozen=True)
class _SnapshotCounts:
    epic_count: int = 0
    issue_count: int = 0
    acceptance_criterion_count: int = 0
    comment_count: int = 0
    label_count: int = 0
    assignee_count: int = 0


class PostgresBacklogRepository:
    """Persist and reconstruct canonical backlogs in PostgreSQL.

    Imports are full, transactional replacements of the selected provider
    project's backlog item snapshot. Project/account identity rows are
    upserted, all prior items for the project are removed, and the incoming
    domain tree is inserted. Optional round-trip validation runs inside the
    same transaction so any semantic mismatch rolls the entire replacement
    back.
    """

    def __init__(
        self,
        database_url: str,
        *,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        if not database_url or not database_url.strip():
            raise ValueError("database_url is required")

        self._database_url = database_url.strip()
        self._connection_factory = connection_factory

    def check(self) -> DatabaseStatus:
        """Check connectivity, schema tables, and provider seed readiness."""
        with self._connection() as conn:
            identity = conn.execute(
                """
                SELECT
                    current_database() AS database,
                    current_user AS database_user,
                    current_setting('server_version') AS server_version
                """
            ).fetchone()

            table_rows = conn.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name
                """,
                (DATABASE_SCHEMA,),
            ).fetchall()

            available_tables = tuple(row["table_name"] for row in table_rows)
            available_set = set(available_tables)
            missing_tables = tuple(
                table_name
                for table_name in EXPECTED_TABLES
                if table_name not in available_set
            )

            provider_count = 0
            if "providers" in available_set:
                provider_row = conn.execute(
                    """
                    SELECT count(*) AS provider_count
                    FROM providers
                    WHERE deleted_at IS NULL
                    """
                ).fetchone()
                provider_count = int(provider_row["provider_count"])

        return DatabaseStatus(
            database=str(identity["database"]),
            database_user=str(identity["database_user"]),
            schema=DATABASE_SCHEMA,
            server_version=str(identity["server_version"]),
            available_tables=available_tables,
            missing_tables=missing_tables,
            provider_count=provider_count,
        )

    def replace(
        self,
        backlog: Backlog,
        *,
        user_display_name: str,
        user_primary_email: str | None,
        provider_account_username: str,
        provider_account_display_name: str | None,
        verify: bool = True,
    ) -> BacklogImportResult:
        """Atomically replace a provider project's complete backlog snapshot."""
        _validate_snapshot(backlog)

        location = BacklogLocation(
            provider=backlog.project.provider,
            provider_account_username=provider_account_username,
            project_title=backlog.project.title,
        )
        counts = _count_snapshot(backlog)

        with self._connection() as conn:
            user_id = self._upsert_user(
                conn,
                display_name=user_display_name,
                primary_email=user_primary_email,
            )
            provider_id = self._upsert_provider(
                conn,
                key=backlog.project.provider,
            )
            provider_account_id = self._upsert_provider_account(
                conn,
                user_id=user_id,
                provider_id=provider_id,
                username=provider_account_username,
                display_name=provider_account_display_name,
            )
            provider_project_id = self._upsert_provider_project(
                conn,
                provider_account_id=provider_account_id,
                project=backlog.project,
            )

            # This is deliberately a snapshot replacement, not a merge. The
            # enclosing connection context commits only after all inserts and
            # optional verification succeed.
            conn.execute(
                "DELETE FROM backlog_items WHERE provider_project_id = %s",
                (provider_project_id,),
            )

            for epic in sorted(backlog.epics, key=_item_sort_key):
                epic_row_id = self._insert_backlog_item(
                    conn,
                    provider_project_id=provider_project_id,
                    parent_item_id=None,
                    item=epic,
                    provider_key=backlog.project.provider,
                )
                self._insert_item_children(conn, epic_row_id, epic)

                for issue in sorted(epic.issues, key=_item_sort_key):
                    issue_row_id = self._insert_backlog_item(
                        conn,
                        provider_project_id=provider_project_id,
                        parent_item_id=epic_row_id,
                        item=issue,
                        provider_key=backlog.project.provider,
                    )
                    self._insert_item_children(conn, issue_row_id, issue)

            if verify:
                persisted = self._load_backlog(conn, location)
                _assert_semantically_equal(backlog, persisted)

        return BacklogImportResult(
            location=location,
            provider_project_id=provider_project_id,
            epic_count=counts.epic_count,
            issue_count=counts.issue_count,
            acceptance_criterion_count=counts.acceptance_criterion_count,
            comment_count=counts.comment_count,
            label_count=counts.label_count,
            assignee_count=counts.assignee_count,
            verified=verify,
        )

    def load(self, location: BacklogLocation) -> Backlog:
        """Load a persisted provider project into the canonical domain model."""
        with self._connection() as conn:
            return self._load_backlog(conn, location)

    @contextmanager
    def _connection(self) -> Iterator[ConnectionLike]:
        try:
            connection = self._make_connection()
            with connection as conn:
                conn.execute(f"SET search_path TO {DATABASE_SCHEMA}, public")
                yield conn
        except BacklogPersistenceError:
            raise
        except Exception as exc:
            raise BacklogPersistenceError(
                f"PostgreSQL backlog persistence failed: {exc}"
            ) from exc

    def _make_connection(self) -> ConnectionLike:
        if self._connection_factory is not None:
            return self._connection_factory(self._database_url)

        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise BacklogPersistenceError(
                "PostgreSQL support is not installed. Run `uv sync` to install "
                "the psycopg dependency."
            ) from exc

        return psycopg.connect(
            self._database_url,
            row_factory=dict_row,
            connect_timeout=10,
            application_name="johnny-johnny-agent",
        )

    @staticmethod
    def _upsert_user(
        conn: ConnectionLike,
        *,
        display_name: str,
        primary_email: str | None,
    ) -> Any:
        if primary_email:
            row = conn.execute(
                """
                INSERT INTO users (display_name, primary_email)
                VALUES (%s, %s)
                ON CONFLICT ((lower(primary_email)))
                    WHERE primary_email IS NOT NULL AND deleted_at IS NULL
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    deleted_at = NULL
                RETURNING id
                """,
                (display_name, primary_email),
            ).fetchone()
            return _required_id(row, "user")

        row = conn.execute(
            """
            SELECT id FROM users
            WHERE display_name = %s
              AND primary_email IS NULL
              AND deleted_at IS NULL
            ORDER BY created_at
            LIMIT 1
            """,
            (display_name,),
        ).fetchone()
        if row:
            return row["id"]

        row = conn.execute(
            """
            INSERT INTO users (display_name, primary_email)
            VALUES (%s, NULL)
            RETURNING id
            """,
            (display_name,),
        ).fetchone()
        return _required_id(row, "user")

    @staticmethod
    def _upsert_provider(conn: ConnectionLike, *, key: str) -> Any:
        display_name = _PROVIDER_DISPLAY_NAMES.get(key, key)
        row = conn.execute(
            """
            INSERT INTO providers (key, display_name, enabled)
            VALUES (%s, %s, true)
            ON CONFLICT (key)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                enabled = true,
                deleted_at = NULL
            RETURNING id
            """,
            (key, display_name),
        ).fetchone()
        return _required_id(row, "provider")

    @staticmethod
    def _upsert_provider_account(
        conn: ConnectionLike,
        *,
        user_id: Any,
        provider_id: Any,
        username: str,
        display_name: str | None,
    ) -> Any:
        row = conn.execute(
            """
            INSERT INTO provider_accounts (
                user_id,
                provider_id,
                username,
                display_name
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (provider_id, (lower(username)))
                WHERE deleted_at IS NULL
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                display_name = EXCLUDED.display_name,
                deleted_at = NULL
            RETURNING id
            """,
            (user_id, provider_id, username, display_name),
        ).fetchone()
        return _required_id(row, "provider account")

    @staticmethod
    def _upsert_provider_project(
        conn: ConnectionLike,
        *,
        provider_account_id: Any,
        project: Project,
    ) -> Any:
        provider_metadata = _copy_json(project.provider_metadata)
        provider_values = _provider_values(
            provider_metadata,
            project.provider,
        )
        external_id = provider_values.get("project_id") or provider_values.get("id")

        row = conn.execute(
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
            ON CONFLICT (provider_account_id, (lower(title)))
                WHERE deleted_at IS NULL
            DO UPDATE SET
                external_id = EXCLUDED.external_id,
                external_number = EXCLUDED.external_number,
                url = EXCLUDED.url,
                provider_metadata = EXCLUDED.provider_metadata,
                deleted_at = NULL
            RETURNING id
            """,
            (
                provider_account_id,
                external_id,
                project.number,
                project.title,
                project.url,
                _jsonb(provider_metadata),
            ),
        ).fetchone()
        return _required_id(row, "provider project")

    @staticmethod
    def _insert_backlog_item(
        conn: ConnectionLike,
        *,
        provider_project_id: Any,
        parent_item_id: Any | None,
        item: Epic | Issue,
        provider_key: str,
    ) -> Any:
        provider_metadata = _copy_json(item.provider_metadata)
        provider_values = _provider_values(provider_metadata, provider_key)

        row = conn.execute(
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
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                provider_project_id,
                parent_item_id,
                item.id,
                item.type,
                item.title,
                item.description,
                item.repository,
                item.status,
                item.issue_state,
                item.order,
                item.milestone,
                provider_values.get("issue_id") or provider_values.get("id"),
                provider_values.get("database_id"),
                provider_values.get("number"),
                provider_values.get("url"),
                provider_values.get("project_item_id"),
                _jsonb(provider_metadata),
            ),
        ).fetchone()
        return _required_id(row, f"backlog item {item.id}")

    @staticmethod
    def _insert_item_children(
        conn: ConnectionLike,
        backlog_item_id: Any,
        item: Epic | Issue,
    ) -> None:
        for position, body in enumerate(item.acceptance_criteria, start=1):
            conn.execute(
                """
                INSERT INTO backlog_item_acceptance_criteria (
                    backlog_item_id,
                    position,
                    body,
                    checked
                )
                VALUES (%s, %s, %s, false)
                """,
                (backlog_item_id, position, body),
            )

        for position, comment in enumerate(item.comments, start=1):
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
                    comment.id,
                    position,
                    comment.body,
                    comment.source,
                    comment.created_at,
                    _jsonb(_copy_json(comment.provider_metadata)),
                ),
            )

        # Labels and assignees are set-like in the current database schema;
        # preserving their source order would require a future position column.
        for label in dict.fromkeys(item.labels):
            conn.execute(
                """
                INSERT INTO backlog_item_labels (backlog_item_id, label)
                VALUES (%s, %s)
                """,
                (backlog_item_id, label),
            )

        for assignee in dict.fromkeys(item.assignees):
            conn.execute(
                """
                INSERT INTO backlog_item_assignees (backlog_item_id, assignee)
                VALUES (%s, %s)
                """,
                (backlog_item_id, assignee),
            )

    def _load_backlog(
        self,
        conn: ConnectionLike,
        location: BacklogLocation,
    ) -> Backlog:
        project_row = conn.execute(
            """
            SELECT
                pp.*,
                p.key AS provider_key,
                pa.username AS provider_account_username
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
            (
                location.provider,
                location.provider_account_username,
                location.project_title,
            ),
        ).fetchone()

        if not project_row:
            raise ProviderProjectNotFoundError(
                f"Provider project not found: {location.describe()}"
            )

        provider_key = str(project_row["provider_key"])
        provider_project_id = project_row["id"]

        item_rows = conn.execute(
            """
            SELECT * FROM backlog_items
            WHERE provider_project_id = %s
              AND deleted_at IS NULL
            ORDER BY
                CASE WHEN parent_item_id IS NULL THEN 0 ELSE 1 END,
                parent_item_id NULLS FIRST,
                item_order,
                canonical_id
            """,
            (provider_project_id,),
        ).fetchall()

        acceptance_rows = conn.execute(
            """
            SELECT ac.backlog_item_id, ac.body
            FROM backlog_item_acceptance_criteria ac
            JOIN backlog_items i ON i.id = ac.backlog_item_id
            WHERE i.provider_project_id = %s
              AND i.deleted_at IS NULL
              AND ac.deleted_at IS NULL
            ORDER BY ac.backlog_item_id, ac.position
            """,
            (provider_project_id,),
        ).fetchall()

        comment_rows = conn.execute(
            """
            SELECT
                c.id,
                c.backlog_item_id,
                c.canonical_comment_id,
                c.body,
                c.source,
                c.created_at,
                c.provider_metadata
            FROM backlog_item_comments c
            JOIN backlog_items i ON i.id = c.backlog_item_id
            WHERE i.provider_project_id = %s
              AND i.deleted_at IS NULL
              AND c.deleted_at IS NULL
            ORDER BY c.backlog_item_id, c.position
            """,
            (provider_project_id,),
        ).fetchall()

        label_rows = conn.execute(
            """
            SELECT l.backlog_item_id, l.label
            FROM backlog_item_labels l
            JOIN backlog_items i ON i.id = l.backlog_item_id
            WHERE i.provider_project_id = %s
              AND i.deleted_at IS NULL
            ORDER BY l.backlog_item_id, l.label
            """,
            (provider_project_id,),
        ).fetchall()

        assignee_rows = conn.execute(
            """
            SELECT a.backlog_item_id, a.assignee
            FROM backlog_item_assignees a
            JOIN backlog_items i ON i.id = a.backlog_item_id
            WHERE i.provider_project_id = %s
              AND i.deleted_at IS NULL
            ORDER BY a.backlog_item_id, a.assignee
            """,
            (provider_project_id,),
        ).fetchall()

        acceptance_by_item: dict[Any, list[str]] = defaultdict(list)
        for row in acceptance_rows:
            acceptance_by_item[row["backlog_item_id"]].append(str(row["body"]))

        comments_by_item: dict[Any, list[Comment]] = defaultdict(list)
        for row in comment_rows:
            comment_id = row.get("canonical_comment_id") or str(row["id"])
            comments_by_item[row["backlog_item_id"]].append(
                Comment(
                    id=str(comment_id),
                    body=str(row["body"]),
                    source=str(row.get("source") or "johnny-johnny"),
                    created_at=_isoformat(row.get("created_at")),
                    provider_metadata=_copy_json(row.get("provider_metadata") or {}),
                )
            )

        labels_by_item: dict[Any, list[str]] = defaultdict(list)
        for row in label_rows:
            labels_by_item[row["backlog_item_id"]].append(str(row["label"]))

        assignees_by_item: dict[Any, list[str]] = defaultdict(list)
        for row in assignee_rows:
            assignees_by_item[row["backlog_item_id"]].append(
                str(row["assignee"])
            )

        epic_by_row_id: dict[Any, Epic] = {}
        epics: list[Epic] = []
        issue_rows: list[Mapping[str, Any]] = []

        for row in item_rows:
            if row.get("parent_item_id") is not None:
                issue_rows.append(row)
                continue

            if row["item_type"] != "epic":
                raise BacklogPersistenceError(
                    f"Root backlog item {row['canonical_id']} is not an epic"
                )

            epic = Epic(
                **self._item_common_fields(
                    row,
                    provider_key=provider_key,
                    acceptance_by_item=acceptance_by_item,
                    comments_by_item=comments_by_item,
                    labels_by_item=labels_by_item,
                    assignees_by_item=assignees_by_item,
                ),
                issues=[],
            )
            epic_by_row_id[row["id"]] = epic
            epics.append(epic)

        for row in issue_rows:
            if row["item_type"] != "issue":
                raise BacklogPersistenceError(
                    f"Nested backlog item {row['canonical_id']} is not an issue"
                )

            parent = epic_by_row_id.get(row["parent_item_id"])
            if parent is None:
                raise BacklogPersistenceError(
                    f"Backlog issue {row['canonical_id']} references a missing epic"
                )

            parent.issues.append(
                Issue(
                    **self._item_common_fields(
                        row,
                        provider_key=provider_key,
                        acceptance_by_item=acceptance_by_item,
                        comments_by_item=comments_by_item,
                        labels_by_item=labels_by_item,
                        assignees_by_item=assignees_by_item,
                    )
                )
            )

        for epic in epics:
            epic.issues.sort(key=_item_sort_key)
        epics.sort(key=_item_sort_key)

        project_metadata = _metadata_with_first_class_values(
            raw_metadata=project_row.get("provider_metadata") or {},
            provider_key=provider_key,
            values={
                "project_id": project_row.get("external_id"),
            },
        )

        return Backlog(
            project=Project(
                provider=provider_key,
                title=str(project_row["title"]),
                number=project_row.get("external_number"),
                url=project_row.get("url"),
                provider_metadata=project_metadata,
            ),
            epics=epics,
        )

    @staticmethod
    def _item_common_fields(
        row: Mapping[str, Any],
        *,
        provider_key: str,
        acceptance_by_item: Mapping[Any, list[str]],
        comments_by_item: Mapping[Any, list[Comment]],
        labels_by_item: Mapping[Any, list[str]],
        assignees_by_item: Mapping[Any, list[str]],
    ) -> dict[str, Any]:
        row_id = row["id"]
        metadata = _metadata_with_first_class_values(
            raw_metadata=row.get("provider_metadata") or {},
            provider_key=provider_key,
            values={
                "issue_id": row.get("external_id"),
                "database_id": row.get("external_database_id"),
                "number": row.get("external_number"),
                "url": row.get("external_url"),
                "project_item_id": row.get("external_project_item_id"),
            },
        )

        return {
            "id": str(row["canonical_id"]),
            "type": str(row["item_type"]),
            "title": str(row["title"]),
            "repository": str(row["repository"]),
            "status": str(row["status"]),
            "issue_state": str(row["issue_state"]),
            "order": int(row["item_order"]),
            "description": str(row.get("description") or ""),
            "acceptance_criteria": list(acceptance_by_item.get(row_id, [])),
            "comments": list(comments_by_item.get(row_id, [])),
            "labels": list(labels_by_item.get(row_id, [])),
            "assignees": list(assignees_by_item.get(row_id, [])),
            "milestone": row.get("milestone"),
            "provider_metadata": metadata,
        }


def _required_id(row: Mapping[str, Any] | None, entity: str) -> Any:
    if not row or row.get("id") is None:
        raise BacklogPersistenceError(
            f"PostgreSQL did not return an id for {entity}"
        )
    return row["id"]


def _jsonb(value: Any) -> Any:
    """Use Psycopg's explicit JSONB adapter when installed.

    Unit tests inject a lightweight fake connection and intentionally run
    without Psycopg. Returning the raw value in that case keeps the domain and
    SQL behavior testable without making the database driver a test import
    requirement.
    """
    try:
        from psycopg.types.json import Jsonb
    except ImportError:
        return value
    return Jsonb(value)


def _provider_values(
    provider_metadata: Mapping[str, Any],
    provider_key: str,
) -> Mapping[str, Any]:
    values = provider_metadata.get(provider_key, {})
    return values if isinstance(values, Mapping) else {}


def _metadata_with_first_class_values(
    *,
    raw_metadata: Mapping[str, Any],
    provider_key: str,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = _copy_json(raw_metadata)
    present_values = {key: value for key, value in values.items() if value is not None}
    if not present_values:
        return metadata

    provider_values = metadata.get(provider_key)
    if not isinstance(provider_values, dict):
        provider_values = {}
        metadata[provider_key] = provider_values
    provider_values.update(present_values)
    return metadata


def _copy_json(value: Any) -> Any:
    if value is None:
        return {}
    return deepcopy(value)


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _item_sort_key(item: Epic | Issue) -> tuple[int, str]:
    return item.order, item.id


def _count_snapshot(backlog: Backlog) -> _SnapshotCounts:
    all_items: list[Epic | Issue] = []
    for epic in backlog.epics:
        all_items.append(epic)
        all_items.extend(epic.issues)

    return _SnapshotCounts(
        epic_count=len(backlog.epics),
        issue_count=sum(len(epic.issues) for epic in backlog.epics),
        acceptance_criterion_count=sum(
            len(item.acceptance_criteria) for item in all_items
        ),
        comment_count=sum(len(item.comments) for item in all_items),
        label_count=sum(len(set(item.labels)) for item in all_items),
        assignee_count=sum(len(set(item.assignees)) for item in all_items),
    )


def _validate_snapshot(backlog: Backlog) -> None:
    if not backlog.project.provider.strip():
        raise BacklogPersistenceError("Backlog project provider is required")
    if not backlog.project.title.strip():
        raise BacklogPersistenceError("Backlog project title is required")

    canonical_ids: set[str] = set()
    comment_ids: set[tuple[str, str]] = set()

    for epic in backlog.epics:
        if epic.type != "epic":
            raise BacklogPersistenceError(
                f"Top-level backlog item {epic.id} must have type 'epic'"
            )
        _validate_item_identity(epic, canonical_ids, comment_ids)

        for issue in epic.issues:
            if issue.type != "issue":
                raise BacklogPersistenceError(
                    f"Nested backlog item {issue.id} must have type 'issue'"
                )
            _validate_item_identity(issue, canonical_ids, comment_ids)


def _validate_item_identity(
    item: Epic | Issue,
    canonical_ids: set[str],
    comment_ids: set[tuple[str, str]],
) -> None:
    if item.id in canonical_ids:
        raise BacklogPersistenceError(
            f"Duplicate canonical backlog item id: {item.id}"
        )
    canonical_ids.add(item.id)

    for comment in item.comments:
        identity = (item.id, comment.id)
        if identity in comment_ids:
            raise BacklogPersistenceError(
                f"Duplicate comment id {comment.id} on backlog item {item.id}"
            )
        comment_ids.add(identity)


def _assert_semantically_equal(expected: Backlog, actual: Backlog) -> None:
    expected_document = _semantic_document(expected)
    actual_document = _semantic_document(actual)
    if expected_document == actual_document:
        return

    difference = _first_difference(expected_document, actual_document)
    raise RoundTripValidationError(
        "PostgreSQL round-trip verification failed"
        + (f" at {difference}" if difference else "")
    )


def _semantic_document(backlog: Backlog) -> dict[str, Any]:
    project = {
        "provider": backlog.project.provider,
        "title": backlog.project.title,
        "number": backlog.project.number,
        "url": backlog.project.url,
        "provider_metadata": _normalize_json(backlog.project.provider_metadata),
    }

    return {
        "project": project,
        "epics": [
            _semantic_item(epic, include_issues=True)
            for epic in sorted(backlog.epics, key=_item_sort_key)
        ],
    }


def _semantic_item(item: Epic | Issue, *, include_issues: bool) -> dict[str, Any]:
    document = {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "repository": item.repository,
        "status": item.status,
        "issue_state": item.issue_state,
        "order": item.order,
        "description": item.description,
        "acceptance_criteria": list(item.acceptance_criteria),
        "comments": [
            {
                "id": comment.id,
                "body": comment.body,
                "source": comment.source,
                "created_at": _normalized_timestamp(comment.created_at),
                "provider_metadata": _normalize_json(comment.provider_metadata),
            }
            for comment in item.comments
        ],
        "labels": sorted(set(item.labels)),
        "assignees": sorted(set(item.assignees)),
        "milestone": item.milestone,
        "provider_metadata": _normalize_json(item.provider_metadata),
    }

    if include_issues:
        document["issues"] = [
            _semantic_item(issue, include_issues=False)
            for issue in sorted(item.issues, key=_item_sort_key)  # type: ignore[attr-defined]
        ]

    return document


def _normalized_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return str(value)

    if parsed.tzinfo is None:
        return parsed.isoformat()
    return parsed.astimezone(timezone.utc).isoformat()


def _normalize_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_json(inner)
            for key, inner in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_json(inner) for inner in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _first_difference(expected: Any, actual: Any, path: str = "backlog") -> str | None:
    if type(expected) is not type(actual):
        return f"{path} (expected {type(expected).__name__}, got {type(actual).__name__})"

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        if expected_keys != actual_keys:
            return (
                f"{path} keys (expected {sorted(expected_keys)}, "
                f"got {sorted(actual_keys)})"
            )
        for key in sorted(expected_keys):
            difference = _first_difference(
                expected[key],
                actual[key],
                f"{path}.{key}",
            )
            if difference:
                return difference
        return None

    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path} length (expected {len(expected)}, got {len(actual)})"
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            difference = _first_difference(
                expected_item,
                actual_item,
                f"{path}[{index}]",
            )
            if difference:
                return difference
        return None

    if expected != actual:
        return f"{path} (expected {expected!r}, got {actual!r})"
    return None
