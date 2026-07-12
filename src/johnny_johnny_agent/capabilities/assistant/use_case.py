"""Application orchestration for Johnny-Johnny assistant capabilities."""

from __future__ import annotations

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantInvocationRequest,
    AssistantModel,
    AssistantResponse,
    AssistantResponseRequest,
    AssistantRoute,
    TokenUsage,
)
from johnny_johnny_agent.capabilities.assistant.provider import LanguageModelProvider


_ROUTE_CLASSIFICATION_INSTRUCTIONS = """
Classify the user's request into exactly one Johnny-Johnny route.

Return exactly one of these values and no other text:

general_chat
backlog

Use backlog when the user is asking to find, inspect, create, update, move,
comment on, delete, reconcile, or otherwise work with a Johnny-Johnny backlog
item, issue, epic, story, project backlog, or backlog status.

Use general_chat for everything else.
""".strip()

_BACKLOG_PLACEHOLDER = (
    "I recognized this as a backlog request. "
    "Backlog retrieval and execution are not connected yet."
)


class GenerateAssistantResponse:
    """Coordinate authenticated Johnny-Johnny assistant requests."""

    def __init__(self, language_model_provider: LanguageModelProvider) -> None:
        self._language_model_provider = language_model_provider

    def available_models(self) -> tuple[AssistantModel, ...]:
        """Expose only the provider-neutral model catalog configured by the server."""
        return self._language_model_provider.available_models()

    def execute(self, request: AssistantInvocationRequest) -> AssistantResponse:
        """Route one authenticated assistant invocation."""
        text = request.text.strip()
        if not text:
            raise ValueError("Assistant response text must not be empty.")

        model = request.model.strip() if request.model is not None else None
        if model == "":
            raise ValueError("Assistant model must not be blank when provided.")

        classification = self._language_model_provider.generate(
            AssistantResponseRequest(
                text=text,
                model=model,
                instructions=_ROUTE_CLASSIFICATION_INSTRUCTIONS,
            )
        )
        route = self._parse_route(classification.text)

        if route is AssistantRoute.BACKLOG:
            return AssistantResponse(
                response_id=classification.response_id,
                text=_BACKLOG_PLACEHOLDER,
                model=classification.model,
                usage=classification.usage,
            )

        response = self._language_model_provider.generate(
            AssistantResponseRequest(
                text=text,
                model=model,
            )
        )
        return AssistantResponse(
            response_id=response.response_id,
            text=response.text,
            model=response.model,
            usage=TokenUsage(
                input_tokens=(
                        classification.usage.input_tokens
                        + response.usage.input_tokens
                ),
                output_tokens=(
                        classification.usage.output_tokens
                        + response.usage.output_tokens
                ),
            ),
        )

    @staticmethod
    def _parse_route(value: str) -> AssistantRoute:
        normalized = value.strip().lower()
        try:
            return AssistantRoute(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Assistant route classification was invalid: {value!r}"
            ) from exc