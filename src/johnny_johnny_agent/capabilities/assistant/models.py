"""Provider-neutral assistant request and response models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantResponseRequest:
    """Text submitted to the Johnny-Johnny assistant capability."""

    text: str


@dataclass(frozen=True)
class TokenUsage:
    """Normalized language-model token counts."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class AssistantResponse:
    """Normalized assistant output returned by any language-model provider."""

    response_id: str
    text: str
    model: str
    usage: TokenUsage
