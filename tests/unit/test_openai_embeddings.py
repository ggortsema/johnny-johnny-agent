from __future__ import annotations

from types import SimpleNamespace

import pytest

from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingInvalidResponseError,
    EmbeddingVector,
)
from johnny_johnny_agent.config import OpenAIEmbeddingSettings
from johnny_johnny_agent.providers.openai_embeddings import (
    OpenAIEmbeddingProvider,
)


class _FakeEmbeddings:
    def __init__(self, result):
        self.result = result
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.result


def _provider(
        embeddings: _FakeEmbeddings,
        *,
        dimensions: int = 3,
) -> OpenAIEmbeddingProvider:
    return OpenAIEmbeddingProvider(
        OpenAIEmbeddingSettings(
            api_key="test-secret",
            model="text-embedding-3-small",
            dimensions=dimensions,
        ),
        client=SimpleNamespace(embeddings=embeddings),
    )


def test_openai_embedding_adapter_batches_texts_and_preserves_input_order():
    embeddings = _FakeEmbeddings(
        SimpleNamespace(
            data=[
                SimpleNamespace(
                    index=1,
                    embedding=[0.4, 0.5, 0.6],
                ),
                SimpleNamespace(
                    index=0,
                    embedding=[0.1, 0.2, 0.3],
                ),
            ]
        )
    )

    vectors = _provider(embeddings).embed_texts(
        (
            "First backlog document",
            "Second backlog document",
        )
    )

    assert embeddings.requests == [
        {
            "model": "text-embedding-3-small",
            "input": [
                "First backlog document",
                "Second backlog document",
            ],
            "dimensions": 3,
            "encoding_format": "float",
        }
    ]

    assert vectors == (
        EmbeddingVector(
            values=(0.1, 0.2, 0.3),
            model="text-embedding-3-small",
            dimensions=3,
        ),
        EmbeddingVector(
            values=(0.4, 0.5, 0.6),
            model="text-embedding-3-small",
            dimensions=3,
        ),
    )


def test_openai_embedding_adapter_returns_empty_without_provider_call():
    embeddings = _FakeEmbeddings(
        SimpleNamespace(data=[]),
    )

    vectors = _provider(embeddings).embed_texts(())

    assert vectors == ()
    assert embeddings.requests == []


def test_openai_embedding_adapter_rejects_blank_text_before_provider_call():
    embeddings = _FakeEmbeddings(
        SimpleNamespace(data=[]),
    )

    with pytest.raises(
            ValueError,
            match="Embedding input text must not be blank",
    ):
        _provider(embeddings).embed_texts(
            (
                "Valid text",
                "   ",
            )
        )

    assert embeddings.requests == []


def test_openai_embedding_adapter_rejects_wrong_vector_count():
    embeddings = _FakeEmbeddings(
        SimpleNamespace(
            data=[
                SimpleNamespace(
                    index=0,
                    embedding=[0.1, 0.2, 0.3],
                )
            ]
        )
    )

    with pytest.raises(
            EmbeddingInvalidResponseError,
            match="wrong number of vectors",
    ):
        _provider(embeddings).embed_texts(
            (
                "First document",
                "Second document",
            )
        )


def test_openai_embedding_adapter_rejects_wrong_dimensions():
    embeddings = _FakeEmbeddings(
        SimpleNamespace(
            data=[
                SimpleNamespace(
                    index=0,
                    embedding=[0.1, 0.2],
                )
            ]
        )
    )

    with pytest.raises(
            EmbeddingInvalidResponseError,
            match="wrong number of dimensions",
    ):
        _provider(embeddings).embed_texts(
            ("One document",)
        )