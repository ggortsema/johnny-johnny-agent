"""Application orchestration for Johnny-Johnny assistant capabilities."""

from __future__ import annotations

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantModel,
    AssistantResponse,
    AssistantResponseRequest,
)
from johnny_johnny_agent.capabilities.assistant.provider import LanguageModelProvider


class GenerateAssistantResponse:
    """Stable orchestration boundary for assistant response generation.

    Retrieval, memory, tool execution, prompt construction, and provider selection
    can be coordinated here later without changing the public HTTP route.
    """

    def __init__(self, language_model_provider: LanguageModelProvider) -> None:
        self._language_model_provider = language_model_provider

    def available_models(self) -> tuple[AssistantModel, ...]:
        """Expose only the provider-neutral model catalog configured by the server."""
        return self._language_model_provider.available_models()

    def execute(self, request: AssistantResponseRequest) -> AssistantResponse:
        """Generate one response through the configured provider boundary."""
        text = request.text.strip()
        if not text:
            raise ValueError("Assistant response text must not be empty.")

        model = request.model.strip() if request.model is not None else None
        if model == "":
            raise ValueError("Assistant model must not be blank when provided.")

        return self._language_model_provider.generate(
            AssistantResponseRequest(text=text, model=model)
        )
