"""Language-model provider port and provider-neutral failures."""

from __future__ import annotations

from typing import Protocol

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantModel,
    AssistantResponse,
    AssistantResponseRequest,
)


class LanguageModelProvider(Protocol):
    """Generate responses and describe server-allowed model choices."""

    def available_models(self) -> tuple[AssistantModel, ...]:
        """Return model choices safe for an authenticated client to request."""

    def generate(self, request: AssistantResponseRequest) -> AssistantResponse:
        """Generate and normalize one assistant response."""


class LanguageModelProviderError(RuntimeError):
    """Base failure raised by a language-model provider adapter."""


class UnsupportedLanguageModelError(RuntimeError):
    """The client requested a model not present in server configuration."""

    def __init__(self, model: str, available_models: tuple[str, ...]) -> None:
        self.model = model
        self.available_models = available_models
        super().__init__(f"Assistant model '{model}' is not available.")


class LanguageModelAuthenticationError(LanguageModelProviderError):
    """The server-owned provider credential was rejected."""


class LanguageModelTimeoutError(LanguageModelProviderError):
    """The provider did not complete the request before its deadline."""


class LanguageModelUnavailableError(LanguageModelProviderError):
    """The provider is temporarily unreachable or cannot accept the request."""


class LanguageModelInvalidResponseError(LanguageModelProviderError):
    """The provider returned data that cannot satisfy the application contract."""
