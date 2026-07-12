"""OpenAI adapter for provider-neutral semantic embeddings."""

from __future__ import annotations

from typing import Any, Protocol

import openai
from openai import OpenAI

from johnny_johnny_agent.capabilities.semantic_retrieval.embeddings import (
    EmbeddingAuthenticationError,
    EmbeddingInvalidResponseError,
    EmbeddingProviderError,
    EmbeddingTimeoutError,
    EmbeddingUnavailableError,
    EmbeddingVector,
)
from johnny_johnny_agent.config import OpenAIEmbeddingSettings


class _EmbeddingsResource(Protocol):
    def create(self, **kwargs: Any) -> Any:
        """Create one batch of embeddings."""


class _OpenAIClient(Protocol):
    embeddings: _EmbeddingsResource


class OpenAIEmbeddingProvider:
    """Create normalized semantic vectors with OpenAI."""

    def __init__(
            self,
            settings: OpenAIEmbeddingSettings,
            *,
            client: _OpenAIClient | None = None,
    ) -> None:
        self._model = settings.model
        self._dimensions = settings.dimensions
        self._client = client or OpenAI(api_key=settings.api_key)

    @property
    def model(self) -> str:
        """Return the configured OpenAI embedding model."""
        return self._model

    @property
    def dimensions(self) -> int:
        """Return the configured OpenAI embedding dimensions."""
        return self._dimensions

    def embed_texts(
            self,
            texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        """Create one embedding for each supplied text."""

        if not texts:
            return ()

        if any(not text.strip() for text in texts):
            raise ValueError("Embedding input text must not be blank.")

        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=list(texts),
                dimensions=self._dimensions,
                encoding_format="float",
            )
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            raise EmbeddingAuthenticationError(
                "The embedding provider rejected the configured credential."
            ) from exc
        except openai.APITimeoutError as exc:
            raise EmbeddingTimeoutError(
                "The embedding provider request timed out."
            ) from exc
        except (openai.APIConnectionError, openai.RateLimitError) as exc:
            raise EmbeddingUnavailableError(
                "The embedding provider is temporarily unavailable."
            ) from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise EmbeddingUnavailableError(
                    "The embedding provider is temporarily unavailable."
                ) from exc

            raise EmbeddingProviderError(
                "The embedding provider rejected the request."
            ) from exc
        except openai.APIError as exc:
            raise EmbeddingProviderError(
                "The embedding provider could not complete the request."
            ) from exc

        data = sorted(response.data, key=lambda item: item.index)

        if len(data) != len(texts):
            raise EmbeddingInvalidResponseError(
                "The embedding provider returned the wrong number of vectors."
            )

        vectors: list[EmbeddingVector] = []

        for item in data:
            values = tuple(float(value) for value in item.embedding)

            if len(values) != self._dimensions:
                raise EmbeddingInvalidResponseError(
                    "The embedding provider returned a vector with "
                    "the wrong number of dimensions."
                )

            vectors.append(
                EmbeddingVector(
                    values=values,
                    model=self._model,
                    dimensions=self._dimensions,
                )
            )

        return tuple(vectors)