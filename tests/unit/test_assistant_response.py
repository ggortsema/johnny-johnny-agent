from __future__ import annotations

from dataclasses import dataclass

import pytest

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantInvocationRequest,
    AssistantModel,
    AssistantPrincipal,
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
    responses: list[AssistantResponse]

    def available_models(self) -> tuple[AssistantModel, ...]:
        return (
            AssistantModel(
                id="test-model",
                label="Test model",
                is_default=True,
            ),
            AssistantModel(
                id="alternate-model",
                label="Alternate model",
            ),
        )

    def generate(self, request: AssistantResponseRequest) -> AssistantResponse:
        self.requests.append(request)

        if not self.responses:
            raise AssertionError("The test provider received an unexpected request.")

        return self.responses.pop(0)


def _response(
        text: str,
        *,
        response_id: str,
        model: str = "test-model",
        input_tokens: int = 5,
        output_tokens: int = 1,
) -> AssistantResponse:
    return AssistantResponse(
        response_id=response_id,
        text=text,
        model=model,
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def _invocation(
        text: str,
        model: str | None = None,
) -> AssistantInvocationRequest:
    return AssistantInvocationRequest(
        text=text,
        model=model,
        principal=AssistantPrincipal(
            subject="auth0|grant",
            scopes=frozenset(
                {
                    "invoke:assistant",
                    "read:backlogs",
                    "write:backlogs",
                }
            ),
            client_id="native-client",
        ),
    )


def test_general_chat_is_classified_then_sent_through_normal_generation():
    provider = _RecordingProvider(
        requests=[],
        responses=[
            _response(
                "general_chat",
                response_id="classification-123",
                input_tokens=4,
                output_tokens=1,
            ),
            _response(
                "Generated response text.",
                response_id="response-123",
                model="alternate-model",
                input_tokens=7,
                output_tokens=3,
            ),
        ],
    )
    use_case = GenerateAssistantResponse(provider)

    response = use_case.execute(
        _invocation(
            text="  What is the airspeed velocity of a laden swallow?  ",
            model="  alternate-model  ",
        )
    )

    assert len(provider.requests) == 2

    classification_request = provider.requests[0]
    assert (
            classification_request.text
            == "What is the airspeed velocity of a laden swallow?"
    )
    assert classification_request.model == "alternate-model"
    assert classification_request.instructions is not None
    assert "general_chat" in classification_request.instructions
    assert "backlog" in classification_request.instructions

    assert provider.requests[1] == AssistantResponseRequest(
        text="What is the airspeed velocity of a laden swallow?",
        model="alternate-model",
    )

    assert response == AssistantResponse(
        response_id="response-123",
        text="Generated response text.",
        model="alternate-model",
        usage=TokenUsage(
            input_tokens=11,
            output_tokens=4,
        ),
    )


def test_backlog_request_is_classified_and_stops_at_placeholder():
    provider = _RecordingProvider(
        requests=[],
        responses=[
            _response(
                "backlog",
                response_id="classification-456",
                input_tokens=6,
                output_tokens=1,
            )
        ],
    )
    use_case = GenerateAssistantResponse(provider)

    response = use_case.execute(
        _invocation(text="Put the webhook story into progress.")
    )

    assert len(provider.requests) == 1
    assert provider.requests[0].instructions is not None

    assert response == AssistantResponse(
        response_id="classification-456",
        text=(
            "I recognized this as a backlog request. "
            "Backlog retrieval and execution are not connected yet."
        ),
        model="test-model",
        usage=TokenUsage(
            input_tokens=6,
            output_tokens=1,
        ),
    )


def test_invalid_route_classification_fails_safely():
    provider = _RecordingProvider(
        requests=[],
        responses=[
            _response(
                "maybe_backlog",
                response_id="classification-invalid",
            )
        ],
    )
    use_case = GenerateAssistantResponse(provider)

    with pytest.raises(
            ValueError,
            match="Assistant route classification was invalid",
    ):
        use_case.execute(_invocation(text="Do something with my project."))

    assert len(provider.requests) == 1


def test_authenticated_identity_is_not_sent_to_provider():
    provider = _RecordingProvider(
        requests=[],
        responses=[
            _response(
                "backlog",
                response_id="classification-789",
            )
        ],
    )
    use_case = GenerateAssistantResponse(provider)

    use_case.execute(_invocation(text="Update a backlog story."))

    provider_request = provider.requests[0]
    assert not hasattr(provider_request, "principal")
    assert not hasattr(provider_request, "scopes")
    assert not hasattr(provider_request, "subject")


def test_generate_assistant_response_exposes_provider_neutral_model_catalog():
    provider = _RecordingProvider(requests=[], responses=[])

    assert GenerateAssistantResponse(provider).available_models() == (
        AssistantModel(
            id="test-model",
            label="Test model",
            is_default=True,
        ),
        AssistantModel(
            id="alternate-model",
            label="Alternate model",
        ),
    )


def test_generate_assistant_response_rejects_blank_text_before_provider_call():
    provider = _RecordingProvider(requests=[], responses=[])
    use_case = GenerateAssistantResponse(provider)

    with pytest.raises(ValueError, match="must not be empty"):
        use_case.execute(_invocation(text=" \n\t "))

    assert provider.requests == []


def test_generate_assistant_response_rejects_blank_model_before_provider_call():
    provider = _RecordingProvider(requests=[], responses=[])
    use_case = GenerateAssistantResponse(provider)

    with pytest.raises(ValueError, match="must not be blank"):
        use_case.execute(_invocation(text="Hello", model="  "))

    assert provider.requests == []