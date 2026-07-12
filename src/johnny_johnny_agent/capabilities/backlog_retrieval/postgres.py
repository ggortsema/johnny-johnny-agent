"""PostgreSQL persistence for derived backlog-item embeddings."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterator, Mapping, Protocol, Sequence

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogLocation,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.documents import (
    BacklogRetrievalDocument,
)
from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingVector,
)


DATABASE_SCHEMA = "johnny_johnny"


class ConnectionLike(Protocol):
    """Small PostgreSQL connection surface used by this repository."""

    def __enter__(self) -> "ConnectionLike": ...

    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...

    def execute(
            self,
            query: str,
            params: Sequence[Any] | None = None,
    ) -> Any: ...


ConnectionFactory = Callable[[str], ConnectionLike]


class BacklogEmbeddingPersistenceError(RuntimeError):
    """Base failure for derived backlog embedding persistence."""


class CanonicalBacklogItemNotFoundError(BacklogEmbeddingPersistenceError):
    """Raised when an embedding target cannot be resolved."""


@dataclass(frozen=True)
class StoredBacklogItemEmbedding:
    """Metadata for one currently stored backlog-item embedding."""

    backlog_item_id: Any
    canonical_id: str
    source_text: str
    source_hash: str
    embedding_model: str
    embedding_dimensions: int
    embedded_at: datetime


class PostgresBacklogEmbeddingRepository:
    """Persist one current semantic embedding per canonical backlog item."""

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

    def find(
            self,
            location: BacklogLocation,
            canonical_id: str,
    ) -> StoredBacklogItemEmbedding | None:
        """Find current embedding metadata for one canonical backlog item."""
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT
                    embeddings.backlog_item_id,
                    items.canonical_id,
                    embeddings.source_text,
                    embeddings.source_hash,
                    embeddings.embedding_model,
                    embeddings.embedding_dimensions,
                    embeddings.embedded_at
                FROM backlog_item_embeddings AS embeddings
                         JOIN backlog_items AS items
                              ON items.id = embeddings.backlog_item_id
                         JOIN provider_projects AS projects
                              ON projects.id = items.provider_project_id
                         JOIN provider_accounts AS accounts
                              ON accounts.id = projects.provider_account_id
                         JOIN providers
                              ON providers.id = accounts.provider_id
                WHERE providers.key = %s
                  AND lower(accounts.username) = lower(%s)
                  AND lower(projects.title) = lower(%s)
                  AND items.canonical_id = %s
                  AND providers.deleted_at IS NULL
                  AND accounts.deleted_at IS NULL
                  AND projects.deleted_at IS NULL
                  AND items.deleted_at IS NULL
                """,
                (
                    location.provider,
                    location.provider_account_username,
                    location.project_title,
                    canonical_id,
                ),
            ).fetchone()

        return _stored_embedding(row) if row else None

    def upsert(
            self,
            location: BacklogLocation,
            document: BacklogRetrievalDocument,
            vector: EmbeddingVector,
    ) -> StoredBacklogItemEmbedding:
        """Insert or replace one canonical backlog item's embedding."""
        vector_literal = _vector_literal(vector.values)

        with self._connection() as conn:
            row = conn.execute(
                """
                INSERT INTO backlog_item_embeddings (
                    backlog_item_id,
                    source_text,
                    source_hash,
                    embedding_model,
                    embedding_dimensions,
                    embedding,
                    embedded_at
                )
                SELECT
                    items.id,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::public.vector,
                    now()
                FROM backlog_items AS items
                         JOIN provider_projects AS projects
                              ON projects.id = items.provider_project_id
                         JOIN provider_accounts AS accounts
                              ON accounts.id = projects.provider_account_id
                         JOIN providers
                              ON providers.id = accounts.provider_id
                WHERE providers.key = %s
                  AND lower(accounts.username) = lower(%s)
                  AND lower(projects.title) = lower(%s)
                  AND items.canonical_id = %s
                  AND providers.deleted_at IS NULL
                  AND accounts.deleted_at IS NULL
                  AND projects.deleted_at IS NULL
                  AND items.deleted_at IS NULL
                    ON CONFLICT (backlog_item_id)
                DO UPDATE SET
                    source_text = EXCLUDED.source_text,
                                           source_hash = EXCLUDED.source_hash,
                                           embedding_model = EXCLUDED.embedding_model,
                                           embedding_dimensions = EXCLUDED.embedding_dimensions,
                                           embedding = EXCLUDED.embedding,
                                           embedded_at = now()
                                           RETURNING
                                           backlog_item_id,
                                           %s AS canonical_id,
                                           source_text,
                                           source_hash,
                                           embedding_model,
                                           embedding_dimensions,
                                           embedded_at
                """,
                (
                    document.source_text,
                    document.source_hash,
                    vector.model,
                    vector.dimensions,
                    vector_literal,
                    location.provider,
                    location.provider_account_username,
                    location.project_title,
                    document.canonical_id,
                    document.canonical_id,
                ),
            ).fetchone()

        if not row:
            raise CanonicalBacklogItemNotFoundError(
                "Canonical backlog item was not found for embedding: "
                f"{document.canonical_id}"
            )

        return _stored_embedding(row)

    @contextmanager
    def _connection(self) -> Iterator[ConnectionLike]:
        try:
            connection = self._make_connection()
            with connection as conn:
                conn.execute(
                    f"SET search_path TO {DATABASE_SCHEMA}, public"
                )
                yield conn
        except BacklogEmbeddingPersistenceError:
            raise
        except Exception as exc:
            raise BacklogEmbeddingPersistenceError(
                f"PostgreSQL backlog embedding persistence failed: {exc}"
            ) from exc

    def _make_connection(self) -> ConnectionLike:
        if self._connection_factory is not None:
            return self._connection_factory(self._database_url)

        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise BacklogEmbeddingPersistenceError(
                "PostgreSQL support is not installed. Run `uv sync`."
            ) from exc

        return psycopg.connect(
            self._database_url,
            row_factory=dict_row,
            connect_timeout=10,
            application_name="johnny-johnny-agent",
        )


def _vector_literal(values: tuple[float, ...]) -> str:
    """Render a pgvector text literal for a parameterized database cast."""
    return "[" + ",".join(format(value, ".17g") for value in values) + "]"


def _stored_embedding(
        row: Mapping[str, Any],
) -> StoredBacklogItemEmbedding:
    return StoredBacklogItemEmbedding(
        backlog_item_id=row["backlog_item_id"],
        canonical_id=str(row["canonical_id"]),
        source_text=str(row["source_text"]),
        source_hash=str(row["source_hash"]),
        embedding_model=str(row["embedding_model"]),
        embedding_dimensions=int(row["embedding_dimensions"]),
        embedded_at=row["embedded_at"],
    )