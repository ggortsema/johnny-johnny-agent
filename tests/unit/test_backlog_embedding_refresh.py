from __future__ import annotations

from datetime import datetime, timezone

from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogLocation,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.documents import (
    BacklogRetrievalDocument,
    build_backlog_retrieval_document,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.postgres import (
    StoredBacklogItemEmbedding,
)
from johnny_johnny_agent.capabilities.backlog_retrieval.refresh import (
    BacklogEmbeddingRefreshResult,
    EmbeddingRefreshStatus,
    RefreshBacklogItemEmbedding,
)
from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingVector,
)
from johnny_johnny_agent.domain.backlog import Epic, Issue


class _RecordingEmbeddingProvider:
    def __init__(
            self,
            *,
            model: str = "text-embedding-3-small",
            dimensions: int = 3,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self.requests: list[tuple[str, ...]] = []

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_texts(
            self,
            texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        self.requests.append(texts)
        return (
            EmbeddingVector(
                values=(0.1, 0.2, 0.3),
                model=self.model,
                dimensions=self.dimensions,
            ),
        )


class _RecordingRepository:
    def __init__(
            self,
            existing: StoredBacklogItemEmbedding | None,
    ) -> None:
        self.existing = existing
        self.find_calls = []
        self.upsert_calls = []

    def find(self, location, canonical_id):
        self.find_calls.append((location, canonical_id))
        return self.existing

    def upsert(self, location, document, vector):
        self.upsert_calls.append((location, document, vector))
        return _stored_embedding(
            document,
            model=vector.model,
            dimensions=vector.dimensions,
        )


def _location() -> BacklogLocation:
    return BacklogLocation(
        provider="github",
        provider_account_username="ggortsema",
        project_title="Johnny-Johnny Backlog",
    )


def _epic() -> Epic:
    return Epic(
        id="backlog-as-code-synchronization",
        type="epic",
        title="Backlog-as-Code Synchronization",
        repository="ggortsema/johnny-johnny-agent",
        status="In Progress",
        issue_state="open",
        order=1,
        description="Synchronize canonical backlog state with providers.",
        acceptance_criteria=[],
        comments=[],
        labels=[],
        assignees=[],
        provider_metadata={},
    )


def _issue(
        *,
        description: str = "Receive provider-originated GitHub updates.",
) -> Issue:
    return Issue(
        id="implement-github-webhook-synchronization",
        type="issue",
        title="Implement GitHub Webhook Synchronization",
        repository="ggortsema/johnny-johnny-agent",
        status="Ready",
        issue_state="open",
        order=2,
        description=description,
        acceptance_criteria=[
            "Validate webhook signatures.",
        ],
        comments=[],
        labels=[],
        assignees=[],
        provider_metadata={},
    )


def _document() -> BacklogRetrievalDocument:
    return build_backlog_retrieval_document(
        _issue(),
        parent_epic=_epic(),
    )


def _stored_embedding(
        document: BacklogRetrievalDocument,
        *,
        model: str = "text-embedding-3-small",
        dimensions: int = 3,
) -> StoredBacklogItemEmbedding:
    return StoredBacklogItemEmbedding(
        backlog_item_id="database-item-uuid",
        canonical_id=document.canonical_id,
        source_text=document.source_text,
        source_hash=document.source_hash,
        embedding_model=model,
        embedding_dimensions=dimensions,
        embedded_at=datetime(
            2026,
            7,
            12,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_refresh_creates_embedding_when_none_exists():
    provider = _RecordingEmbeddingProvider()
    repository = _RecordingRepository(existing=None)
    use_case = RefreshBacklogItemEmbedding(provider, repository)

    result = use_case.execute(
        _location(),
        _issue(),
        parent_epic=_epic(),
    )

    assert result.status is EmbeddingRefreshStatus.CREATED
    assert len(provider.requests) == 1
    assert len(repository.upsert_calls) == 1


def test_refresh_skips_when_source_model_and_dimensions_match():
    document = _document()
    existing = _stored_embedding(document)
    provider = _RecordingEmbeddingProvider()
    repository = _RecordingRepository(existing=existing)
    use_case = RefreshBacklogItemEmbedding(provider, repository)

    result = use_case.execute(
        _location(),
        _issue(),
        parent_epic=_epic(),
    )

    assert result == BacklogEmbeddingRefreshResult(
        status=EmbeddingRefreshStatus.UNCHANGED,
        embedding=existing,
    )
    assert provider.requests == []
    assert repository.upsert_calls == []


def test_refresh_updates_when_descriptive_text_changes():
    existing = _stored_embedding(_document())
    provider = _RecordingEmbeddingProvider()
    repository = _RecordingRepository(existing=existing)
    use_case = RefreshBacklogItemEmbedding(provider, repository)

    result = use_case.execute(
        _location(),
        _issue(
            description=(
                "Receive, validate, and process provider-originated "
                "GitHub webhook updates."
            )
        ),
        parent_epic=_epic(),
    )

    assert result.status is EmbeddingRefreshStatus.UPDATED
    assert len(provider.requests) == 1
    assert len(repository.upsert_calls) == 1


def test_refresh_updates_when_embedding_model_changes():
    document = _document()
    existing = _stored_embedding(
        document,
        model="older-embedding-model",
    )
    provider = _RecordingEmbeddingProvider(
        model="text-embedding-3-small",
    )
    repository = _RecordingRepository(existing=existing)
    use_case = RefreshBacklogItemEmbedding(provider, repository)

    result = use_case.execute(
        _location(),
        _issue(),
        parent_epic=_epic(),
    )

    assert result.status is EmbeddingRefreshStatus.UPDATED
    assert len(provider.requests) == 1
    assert len(repository.upsert_calls) == 1