from __future__ import annotations

import pytest

from johnny_johnny_agent.api.app import create_app
from johnny_johnny_agent.config import OpenAISettings, resolve_openai_settings


def test_openai_configuration_requires_and_trims_key_and_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "  test-secret  ")
    monkeypatch.setenv("OPENAI_MODEL", "  configured-model  ")

    assert resolve_openai_settings() == OpenAISettings(
        api_key="test-secret",
        model="configured-model",
    )


@pytest.mark.parametrize("missing_name", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_openai_configuration_fails_closed_when_required_value_is_missing(
    monkeypatch,
    missing_name,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    monkeypatch.delenv(missing_name, raising=False)

    with pytest.raises(RuntimeError, match=f"{missing_name} is required"):
        resolve_openai_settings()


@pytest.mark.parametrize("missing_name", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_application_factory_fails_closed_without_openai_configuration(
    monkeypatch,
    missing_name,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    monkeypatch.delenv(missing_name, raising=False)

    with pytest.raises(RuntimeError, match=f"{missing_name} is required"):
        create_app(access_token_verifier=object(), api_docs_enabled=False)


def test_openai_configuration_does_not_expose_key_in_repr():
    settings = OpenAISettings(
        api_key="sensitive-server-key",
        model="configured-model",
    )

    assert "sensitive-server-key" not in repr(settings)
    assert "configured-model" in repr(settings)
