"""Refresh derived semantic embeddings for canonical backlog items."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogLocation,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.documents import (
    build_backlog_retrieval_document,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.postgres import (
    PostgresBacklogEmbeddingRepository,
    StoredBacklogItemEmbedding,
)
from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingProvider,
)
from johnny_johnny_agent.domain.backlog import Epic, Issue


class EmbeddingRefreshStatus(StrEnum):
    """Outcome of one backlog-item embedding refresh."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class BacklogEmbeddingRefreshResult:
    """Result of refreshing one canonical backlog-item embedding."""

    status: EmbeddingRefreshStatus
    embedding: StoredBacklogItemEmbedding


class RefreshBacklogItemEmbedding:
    """Create, replace, or skip one derived backlog-item embedding."""

    def __init__(
            self,
            embedding_provider: EmbeddingProvider,
            repository: PostgresBacklogEmbeddingRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._repository = repository

    def execute(
            self,
            location: BacklogLocation,
            item: Epic | Issue,
            *,
            parent_epic: Epic | None = None,
    ) -> BacklogEmbeddingRefreshResult:
        document = build_backlog_retrieval_document(
            item,
            parent_epic=parent_epic,
        )

        existing = self._repository.find(
            location,
            document.canonical_id,
        )

        if existing is not None and (
                existing.source_hash == document.source_hash
                and existing.embedding_model == self._embedding_provider.model
                and existing.embedding_dimensions == self._embedding_provider.dimensions
        ):
            return BacklogEmbeddingRefreshResult(
                status=EmbeddingRefreshStatus.UNCHANGED,
                embedding=existing,
            )

        vectors = self._embedding_provider.embed_texts(
            (document.source_text,)
        )
        if len(vectors) != 1:
            raise RuntimeError(
                "Embedding provider did not return exactly one vector."
            )

        stored = self._repository.upsert(
            location,
            document,
            vectors[0],
        )

        return BacklogEmbeddingRefreshResult(
            status=(
                EmbeddingRefreshStatus.CREATED
                if existing is None
                else EmbeddingRefreshStatus.UPDATED
            ),
            embedding=stored,
        )