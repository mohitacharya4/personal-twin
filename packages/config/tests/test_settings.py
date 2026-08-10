"""Settings load, validate, and fail loudly."""

from __future__ import annotations

import pytest
from twin_config import ConfigError, Settings, load_settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    reset_settings_cache()


def test_defaults_are_sane() -> None:
    # `_env_file=None` ignores any real .env on the developer's machine.
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.vector_store_backend == "chroma"
    assert settings.retrieval_top_k == 5
    assert settings.chunk_overlap < settings.chunk_size
    assert settings.tracing_enabled is False


def test_cors_origins_split() -> None:
    settings = Settings(_env_file=None, cors_origins="http://a.com, http://b.com ")  # type: ignore[call-arg]
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_blank_api_key_becomes_none() -> None:
    settings = Settings(_env_file=None, anthropic_api_key="   ")  # type: ignore[call-arg]
    assert settings.anthropic_api_key is None


def test_overlap_must_be_below_size() -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        Settings(_env_file=None, chunk_size=200, chunk_overlap=200)  # type: ignore[call-arg]


def test_invalid_port_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWIN_API_PORT", "70000")
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert "TWIN_API_PORT" in str(exc.value)


def test_tracing_requires_key_and_flag() -> None:
    on_no_key = Settings(_env_file=None, langsmith_tracing=True)  # type: ignore[call-arg]
    assert on_no_key.tracing_enabled is False
    fully_on = Settings(  # type: ignore[call-arg]
        _env_file=None, langsmith_tracing=True, langsmith_api_key="ls-x"
    )
    assert fully_on.tracing_enabled is True
