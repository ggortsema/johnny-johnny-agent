"""OpenAI Responses API adapter for the language-model provider port."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import openai
from openai import OpenAI

from johnny_johnny_agent.capabilities.assistant.models import (
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
)
from johnny_johnny_agent.config import OpenAISettings


class _ResponsesResource(Protocol):
    def create(self, **kwargs: Any) -> Any:
        """Create one provider response."""


class _OpenAIClient(Protocol):
    responses: _ResponsesResource


class OpenAILanguageModelProvider:
    """Translate OpenAI Responses API data into Johnny-Johnny models."""

    def __init__(
        self,
        settings: OpenAISettings,
        *,
        client: _OpenAIClient | None = None,
    ) -> None:
        self._model = settings.model
        self._client = client or OpenAI(api_key=settings.api_key)

    def generate(self, request: AssistantResponseRequest) -> AssistantResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                input=request.text,
                store=False,
            )
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            raise LanguageModelAuthenticationError(
                "The language-model provider rejected the configured credential."
            ) from exc
        except openai.APITimeoutError as exc:
            raise LanguageModelTimeoutError(
                "The language-model provider request timed out."
            ) from exc
        except (openai.APIConnectionError, openai.RateLimitError) as exc:
            raise LanguageModelUnavailableError(
                "The language-model provider is temporarily unavailable."
            ) from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LanguageModelUnavailableError(
                    "The language-model provider is temporarily unavailable."
                ) from exc
            raise LanguageModelProviderError(
                "The language-model provider rejected the generation request."
            ) from exc
        except openai.APIError as exc:
            raise LanguageModelProviderError(
                "The language-model provider could not complete the request."
            ) from exc

        response_id = _required_string(response, "id")
        output_text = _required_string(response, "output_text", allow_whitespace=True)
        if not output_text.strip():
            raise LanguageModelInvalidResponseError(
                "The language-model provider returned no generated text."
            )

        configured_or_returned_model = _optional_string(response, "model")
        usage = _value(response, "usage")
        return AssistantResponse(
            response_id=response_id,
            text=output_text,
            model=configured_or_returned_model or self._model,
            usage=TokenUsage(
                input_tokens=_non_negative_int(usage, "input_tokens"),
                output_tokens=_non_negative_int(usage, "output_tokens"),
            ),
        )


def _value(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _optional_string(source: Any, name: str) -> str | None:
    value = _value(source, name)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _required_string(
    source: Any,
    name: str,
    *,
    allow_whitespace: bool = False,
) -> str:
    value = _value(source, name)
    if not isinstance(value, str):
        raise LanguageModelInvalidResponseError(
            f"The language-model provider response is missing {name}."
        )
    if not value.strip():
        raise LanguageModelInvalidResponseError(
            f"The language-model provider response is missing {name}."
        )
    return value if allow_whitespace else value.strip()


def _non_negative_int(source: Any, name: str) -> int:
    value = _value(source, name)
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LanguageModelInvalidResponseError(
            f"The language-model provider returned invalid {name}."
        )
    return value
