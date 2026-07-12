"""Provider-neutral assistant orchestration and model contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssistantRoute(StrEnum):
    """Top-level Johnny-Johnny workflow selected for one request."""

    GENERAL_CHAT = "general_chat"
    BACKLOG = "backlog"


@dataclass(frozen=True)
class AssistantPrincipal:
    """Safe application identity retained during assistant orchestration."""

    subject: str
    scopes: frozenset[str]
    client_id: str | None = None


@dataclass(frozen=True)
class AssistantInvocationRequest:
    """One authenticated request entering Johnny-Johnny orchestration."""

    text: str
    principal: AssistantPrincipal
    model: str | None = None
    conversation_id: str | None = None


@dataclass(frozen=True)
class AssistantResponseRequest:
    """One sanitized request sent to a language-model provider."""

    text: str
    model: str | None = None
    instructions: str | None = None


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
    """Normalized assistant output returned by orchestration."""

    response_id: str
    text: str
    model: str
    usage: TokenUsage