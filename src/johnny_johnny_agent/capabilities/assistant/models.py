"""Provider-neutral assistant request, model, and response contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantResponseRequest:
    """Text submitted to the Johnny-Johnny assistant capability."""

    text: str
    model: str | None = None


@dataclass(frozen=True)
class AssistantModel:
    """One server-allowed language-model choice exposed to clients."""

    id: str
    label: str
    is_default: bool = False


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
