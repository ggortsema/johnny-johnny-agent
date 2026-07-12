"""Provider-neutral embedding contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingVector:
    """One text embedding returned by an embedding provider."""

    values: tuple[float, ...]
    model: str
    dimensions: int

    def __post_init__(self) -> None:
        model = self.model.strip()
        if not model:
            raise ValueError("Embedding model must not be blank.")

        if self.dimensions <= 0:
            raise ValueError("Embedding dimensions must be greater than zero.")

        if len(self.values) != self.dimensions:
            raise ValueError(
                "Embedding vector length does not match its declared dimensions."
            )

        object.__setattr__(self, "model", model)


class EmbeddingProvider(Protocol):
    """Create semantic vectors without exposing provider-specific APIs."""

    @property
    def model(self) -> str:
        """Return the configured embedding model identifier."""

    @property
    def dimensions(self) -> int:
        """Return the configured vector dimensions."""

    def embed_texts(
            self,
            texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        """Create one embedding for each supplied text."""


class EmbeddingProviderError(RuntimeError):
    """Base failure raised by an embedding provider adapter."""


class EmbeddingAuthenticationError(EmbeddingProviderError):
    """The embedding provider rejected the configured credential."""


class EmbeddingTimeoutError(EmbeddingProviderError):
    """The embedding provider request timed out."""


class EmbeddingUnavailableError(EmbeddingProviderError):
    """The embedding provider is temporarily unavailable."""


class EmbeddingInvalidResponseError(EmbeddingProviderError):
    """The provider returned embeddings that violate the application contract."""