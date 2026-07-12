from __future__ import annotations

import pytest

from johnny_johnny_agent.config import (
    OpenAIEmbeddingSettings,
    resolve_openai_embedding_settings,
)


def test_openai_embedding_configuration_loads_and_trims_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "  test-secret  ")
    monkeypatch.setenv(
        "OPENAI_EMBEDDING_MODEL",
        "  text-embedding-3-small  ",
    )
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "1536")

    assert resolve_openai_embedding_settings() == OpenAIEmbeddingSettings(
        api_key="test-secret",
        model="text-embedding-3-small",
        dimensions=1536,
    )


@pytest.mark.parametrize(
    "missing_name",
    [
        "OPENAI_API_KEY",
        "OPENAI_EMBEDDING_MODEL",
        "OPENAI_EMBEDDING_DIMENSIONS",
    ],
)
def test_openai_embedding_configuration_requires_all_values(
        monkeypatch,
        missing_name,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "1536")
    monkeypatch.delenv(missing_name, raising=False)

    with pytest.raises(RuntimeError, match=f"{missing_name} is required"):
        resolve_openai_embedding_settings()


def test_openai_embedding_configuration_rejects_non_integer_dimensions(
        monkeypatch,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "many")

    with pytest.raises(
            RuntimeError,
            match="OPENAI_EMBEDDING_DIMENSIONS must be an integer",
    ):
        resolve_openai_embedding_settings()


@pytest.mark.parametrize("dimensions", ["0", "-1"])
def test_openai_embedding_configuration_rejects_non_positive_dimensions(
        monkeypatch,
        dimensions,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", dimensions)

    with pytest.raises(
            RuntimeError,
            match="OPENAI_EMBEDDING_DIMENSIONS must be greater than zero",
    ):
        resolve_openai_embedding_settings()


def test_openai_embedding_settings_do_not_expose_key_in_repr():
    settings = OpenAIEmbeddingSettings(
        api_key="sensitive-server-key",
        model="text-embedding-3-small",
        dimensions=1536,
    )

    assert "sensitive-server-key" not in repr(settings)
    assert "text-embedding-3-small" in repr(settings)
    assert "1536" in repr(settings)