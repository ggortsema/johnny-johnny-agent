from __future__ import annotations

from datetime import datetime, timezone

import pytest

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogLocation,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.documents import (
    BacklogRetrievalDocument,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.postgres import (
    CanonicalBacklogItemNotFoundError,
    PostgresBacklogEmbeddingRepository,
    StoredBacklogItemEmbedding,
)
from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingVector,
)


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _RecordingConnection:
    def __init__(self, rows):
        self._rows = list(rows)
        self.statements = []
        self.exit_exception_type = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exit_exception_type = exc_type
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))

        if normalized.startswith("SET search_path"):
            return _FakeResult()

        row = self._rows.pop(0) if self._rows else None
        return _FakeResult(row)


def _location() -> BacklogLocation:
    return BacklogLocation(
        provider="github",
        provider_account_username="ggortsema",
        project_title="Johnny-Johnny Backlog",
    )


def _document() -> BacklogRetrievalDocument:
    return BacklogRetrievalDocument(
        canonical_id="implement-github-webhook-synchronization",
        item_type="issue",
        source_text=(
            "Type: Issue\n"
            "Title: Implement GitHub Webhook Synchronization"
        ),
        source_hash="a" * 64,
    )


def _vector() -> EmbeddingVector:
    return EmbeddingVector(
        values=(0.125, -0.25, 0.5),
        model="test-embedding-model",
        dimensions=3,
    )


def test_find_returns_current_embedding_metadata():
    embedded_at = datetime(2026, 7, 12, 17, 45, tzinfo=timezone.utc)
    connection = _RecordingConnection(
        rows=[
            {
                "backlog_item_id": "item-row-1",
                "canonical_id": (
                    "implement-github-webhook-synchronization"
                ),
                "source_text": "Stored source text",
                "source_hash": "b" * 64,
                "embedding_model": "text-embedding-3-small",
                "embedding_dimensions": 1536,
                "embedded_at": embedded_at,
            }
        ]
    )
    repository = PostgresBacklogEmbeddingRepository(
        "postgresql://test",
        connection_factory=lambda _database_url: connection,
    )

    result = repository.find(
        _location(),
        "implement-github-webhook-synchronization",
    )

    assert result == StoredBacklogItemEmbedding(
        backlog_item_id="item-row-1",
        canonical_id="implement-github-webhook-synchronization",
        source_text="Stored source text",
        source_hash="b" * 64,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        embedded_at=embedded_at,
    )

    query, params = connection.statements[1]
    assert "FROM backlog_item_embeddings AS embeddings" in query
    assert params == (
        "github",
        "ggortsema",
        "Johnny-Johnny Backlog",
        "implement-github-webhook-synchronization",
    )


def test_find_returns_none_when_embedding_does_not_exist():
    connection = _RecordingConnection(rows=[None])
    repository = PostgresBacklogEmbeddingRepository(
        "postgresql://test",
        connection_factory=lambda _database_url: connection,
    )

    result = repository.find(
        _location(),
        "missing-item",
    )

    assert result is None


def test_upsert_serializes_vector_and_returns_stored_metadata():
    embedded_at = datetime(2026, 7, 12, 17, 50, tzinfo=timezone.utc)
    connection = _RecordingConnection(
        rows=[
            {
                "backlog_item_id": "item-row-1",
                "canonical_id": (
                    "implement-github-webhook-synchronization"
                ),
                "source_text": _document().source_text,
                "source_hash": _document().source_hash,
                "embedding_model": "test-embedding-model",
                "embedding_dimensions": 3,
                "embedded_at": embedded_at,
            }
        ]
    )
    repository = PostgresBacklogEmbeddingRepository(
        "postgresql://test",
        connection_factory=lambda _database_url: connection,
    )

    result = repository.upsert(
        _location(),
        _document(),
        _vector(),
    )

    assert result.canonical_id == (
        "implement-github-webhook-synchronization"
    )
    assert result.source_hash == "a" * 64
    assert result.embedding_model == "test-embedding-model"
    assert result.embedding_dimensions == 3

    query, params = connection.statements[1]
    assert "INSERT INTO backlog_item_embeddings" in query
    assert "ON CONFLICT (backlog_item_id)" in query

    assert params == (
        _document().source_text,
        "a" * 64,
        "test-embedding-model",
        3,
        "[0.125,-0.25,0.5]",
        "github",
        "ggortsema",
        "Johnny-Johnny Backlog",
        "implement-github-webhook-synchronization",
        "implement-github-webhook-synchronization",
    )


def test_upsert_fails_when_canonical_item_cannot_be_resolved():
    connection = _RecordingConnection(rows=[None])
    repository = PostgresBacklogEmbeddingRepository(
        "postgresql://test",
        connection_factory=lambda _database_url: connection,
    )

    with pytest.raises(
            CanonicalBacklogItemNotFoundError,
            match="implement-github-webhook-synchronization",
    ):
        repository.upsert(
            _location(),
            _document(),
            _vector(),
        )
    