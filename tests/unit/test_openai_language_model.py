from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from johnny_johnny_agent.capabilities.assistant.models import (
    AssistantModel,
    AssistantResponse,
    AssistantResponseRequest,
    TokenUsage,
)
from johnny_johnny_agent.capabilities.assistant.provider import (
    LanguageModelAuthenticationError,
    LanguageModelInvalidResponseError,
    LanguageModelProviderError,
    LanguageModelTimeoutError,
    LanguageModelUnavailableError,
    UnsupportedLanguageModelError,
)
from johnny_johnny_agent.config import OpenAISettings
from johnny_johnny_agent.providers.openai_language_model import (
    OpenAILanguageModelProvider,
)


@dataclass
class _FakeResponses:
    result: Any = None
    failure: Exception | None = None

    def __post_init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return self.result


@dataclass
class _FakeClient:
    responses: _FakeResponses


def _provider(
    responses: _FakeResponses,
    *,
    models: tuple[str, ...] = ("configured-model", "alternate-model"),
) -> OpenAILanguageModelProvider:
    return OpenAILanguageModelProvider(
        OpenAISettings(
            api_key="server-owned-key",
            model="configured-model",
            models=models,
        ),
        client=_FakeClient(responses),
    )


def _http_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return httpx.Response(status_code, request=request)


def test_openai_adapter_exposes_server_allowed_model_catalog():
    provider = _provider(_FakeResponses())

    assert provider.available_models() == (
        AssistantModel(
            id="configured-model",
            label="configured-model",
            is_default=True,
        ),
        AssistantModel(
            id="alternate-model",
            label="alternate-model",
            is_default=False,
        ),
    )


def test_openai_adapter_calls_responses_api_and_normalizes_output():
    responses = _FakeResponses(
        result=SimpleNamespace(
            id="resp_123",
            output_text="Generated response text.",
            model="returned-model",
            usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        )
    )

    response = _provider(responses).generate(
        AssistantResponseRequest(text="Explain the story.")
    )

    assert responses.requests == [
        {
            "model": "configured-model",
            "input": "Explain the story.",
            "store": False,
        }
    ]
    assert response == AssistantResponse(
        response_id="resp_123",
        text="Generated response text.",
        model="returned-model",
        usage=TokenUsage(input_tokens=11, output_tokens=7),
    )


def test_openai_adapter_uses_an_allowed_requested_model():
    responses = _FakeResponses(
        result=SimpleNamespace(
            id="resp_alt",
            output_text="Alternate response.",
            model=None,
            usage=None,
        )
    )

    response = _provider(responses).generate(
        AssistantResponseRequest(
            text="Use the alternate model.",
            model="alternate-model",
        )
    )

    assert responses.requests[0]["model"] == "alternate-model"
    assert response.model == "alternate-model"


def test_openai_adapter_rejects_models_outside_server_configuration():
    responses = _FakeResponses()

    with pytest.raises(UnsupportedLanguageModelError) as raised:
        _provider(responses).generate(
            AssistantResponseRequest(text="Hello", model="unconfigured-model")
        )

    assert raised.value.model == "unconfigured-model"
    assert raised.value.available_models == (
        "configured-model",
        "alternate-model",
    )
    assert responses.requests == []


def test_openai_adapter_supports_mapping_responses_and_optional_usage():
    responses = _FakeResponses(
        result={
            "id": "resp_456",
            "output_text": "Mapped response.",
            "usage": None,
        }
    )

    response = _provider(responses).generate(
        AssistantResponseRequest(text="Use a mapping response.")
    )

    assert response == AssistantResponse(
        response_id="resp_456",
        text="Mapped response.",
        model="configured-model",
        usage=TokenUsage(input_tokens=0, output_tokens=0),
    )


@pytest.mark.parametrize(
    "provider_response",
    [
        SimpleNamespace(
            id=None,
            output_text="Generated response text.",
            model="test-model",
            usage=None,
        ),
        SimpleNamespace(
            id="resp_123",
            output_text="   ",
            model="test-model",
            usage=None,
        ),
        SimpleNamespace(
            id="resp_123",
            output_text="Generated response text.",
            model="test-model",
            usage=SimpleNamespace(input_tokens=-1, output_tokens=2),
        ),
    ],
)
def test_openai_adapter_rejects_provider_data_that_cannot_satisfy_contract(
    provider_response,
):
    with pytest.raises(LanguageModelInvalidResponseError):
        _provider(_FakeResponses(result=provider_response)).generate(
            AssistantResponseRequest(text="Hello")
        )


@pytest.mark.parametrize(
    ("provider_error", "application_error"),
    [
        (
            openai.AuthenticationError(
                "invalid key",
                response=_http_response(401),
                body={"error": "invalid key"},
            ),
            LanguageModelAuthenticationError,
        ),
        (
            openai.PermissionDeniedError(
                "forbidden",
                response=_http_response(403),
                body={"error": "forbidden"},
            ),
            LanguageModelAuthenticationError,
        ),
        (
            openai.APITimeoutError(
                httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            LanguageModelTimeoutError,
        ),
        (
            openai.APIConnectionError(
                request=httpx.Request(
                    "POST", "https://api.openai.com/v1/responses"
                )
            ),
            LanguageModelUnavailableError,
        ),
        (
            openai.RateLimitError(
                "rate limited",
                response=_http_response(429),
                body={"error": "rate limited"},
            ),
            LanguageModelUnavailableError,
        ),
        (
            openai.APIStatusError(
                "provider failure",
                response=_http_response(500),
                body={"error": "provider failure"},
            ),
            LanguageModelUnavailableError,
        ),
        (
            openai.APIStatusError(
                "bad request",
                response=_http_response(400),
                body={"error": "bad request"},
            ),
            LanguageModelProviderError,
        ),
    ],
)
def test_openai_adapter_translates_sdk_failures(
    provider_error,
    application_error,
):
    with pytest.raises(application_error):
        _provider(_FakeResponses(failure=provider_error)).generate(
            AssistantResponseRequest(text="Hello")
        )

def test_openai_adapter_passes_internal_instructions_separately():
    responses = _FakeResponses(
        result=SimpleNamespace(
            id="resp_route",
            output_text="general_chat",
            model="configured-model",
            usage=SimpleNamespace(input_tokens=8, output_tokens=1),
        )
    )

    _provider(responses).generate(
        AssistantResponseRequest(
            text="What is the airspeed velocity of a laden swallow?",
            instructions="Classify the request.",
        )
    )

    assert responses.requests == [
        {
            "model": "configured-model",
            "input": "What is the airspeed velocity of a laden swallow?",
            "instructions": "Classify the request.",
            "store": False,
        }
    ]