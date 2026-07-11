"""Language-model provider port and provider-neutral failures."""

from __future__ import annotations

from typing import Protocol

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantResponse,
    AssistantResponseRequest,
)


class LanguageModelProvider(Protocol):
    """Generate one assistant response without exposing provider SDK types."""

    def generate(self, request: AssistantResponseRequest) -> AssistantResponse:
        """Generate and normalize one assistant response."""


class LanguageModelProviderError(RuntimeError):
    """Base failure raised by a language-model provider adapter."""


class LanguageModelAuthenticationError(LanguageModelProviderError):
    """The server-owned provider credential was rejected."""


class LanguageModelTimeoutError(LanguageModelProviderError):
    """The provider did not complete the request before its deadline."""


class LanguageModelUnavailableError(LanguageModelProviderError):
    """The provider is temporarily unreachable or cannot accept the request."""


class LanguageModelInvalidResponseError(LanguageModelProviderError):
    """The provider returned data that cannot satisfy the application contract."""
