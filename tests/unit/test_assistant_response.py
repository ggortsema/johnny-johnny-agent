from __future__ import annotations

from dataclasses import dataclass

import pytest

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantModel,
    AssistantResponse,
    AssistantResponseRequest,
    TokenUsage,
)
from johnny_johnny_agent.capabilities.assistant.use_case import (
    GenerateAssistantResponse,
)


@dataclass
class _RecordingProvider:
    requests: list[AssistantResponseRequest]

    def available_models(self) -> tuple[AssistantModel, ...]:
        return (
            AssistantModel(
                id="test-model",
                label="Test model",
                is_default=True,
            ),
            AssistantModel(id="alternate-model", label="Alternate model"),
        )

    def generate(self, request: AssistantResponseRequest) -> AssistantResponse:
        self.requests.append(request)
        return AssistantResponse(
            response_id="response-123",
            text="Generated response text.",
            model=request.model or "test-model",
            usage=TokenUsage(input_tokens=5, output_tokens=3),
        )


def test_generate_assistant_response_trims_input_and_delegates_to_provider():
    provider = _RecordingProvider(requests=[])
    use_case = GenerateAssistantResponse(provider)

    response = use_case.execute(
        AssistantResponseRequest(
            text="  What should we work on next?  ",
            model="  alternate-model  ",
        )
    )

    assert provider.requests == [
        AssistantResponseRequest(
            text="What should we work on next?",
            model="alternate-model",
        )
    ]
    assert response == AssistantResponse(
        response_id="response-123",
        text="Generated response text.",
        model="alternate-model",
        usage=TokenUsage(input_tokens=5, output_tokens=3),
    )


def test_generate_assistant_response_preserves_server_default_selection():
    provider = _RecordingProvider(requests=[])
    use_case = GenerateAssistantResponse(provider)

    use_case.execute(AssistantResponseRequest(text="Hello"))

    assert provider.requests == [AssistantResponseRequest(text="Hello", model=None)]


def test_generate_assistant_response_exposes_provider_neutral_model_catalog():
    provider = _RecordingProvider(requests=[])

    assert GenerateAssistantResponse(provider).available_models() == (
        AssistantModel(id="test-model", label="Test model", is_default=True),
        AssistantModel(id="alternate-model", label="Alternate model"),
    )


def test_generate_assistant_response_rejects_blank_text_before_provider_call():
    provider = _RecordingProvider(requests=[])
    use_case = GenerateAssistantResponse(provider)

    with pytest.raises(ValueError, match="must not be empty"):
        use_case.execute(AssistantResponseRequest(text=" \n\t "))

    assert provider.requests == []


def test_generate_assistant_response_rejects_blank_model_before_provider_call():
    provider = _RecordingProvider(requests=[])
    use_case = GenerateAssistantResponse(provider)

    with pytest.raises(ValueError, match="must not be blank"):
        use_case.execute(AssistantResponseRequest(text="Hello", model="  "))

    assert provider.requests == []
