"""ModelRegistry resolves roles to models and falls back when a provider isn't buildable."""

from __future__ import annotations

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from twin_config import ModelsConfig, Settings
from twin_rag.registry import ModelRegistry


def _config(profiles: dict[str, dict[str, object]]) -> ModelsConfig:
    return ModelsConfig.model_validate({"default_profile": "p", "profiles": {"p": profiles}})


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg,arg-type]


def test_builds_ollama_generator() -> None:
    config = _config({"generator": {"provider": "ollama", "model": "qwen2.5:7b-instruct"}})
    registry = ModelRegistry(config, _settings())
    model = registry.chat_model("generator")
    assert isinstance(model, BaseChatModel)


def test_builds_ollama_embedder() -> None:
    config = _config({"embedder": {"provider": "ollama", "model": "nomic-embed-text"}})
    registry = ModelRegistry(config, _settings())
    assert isinstance(registry.embedder(), Embeddings)


def test_falls_back_when_primary_unbuildable() -> None:
    # anthropic has no key -> get_llm raises -> registry uses the ollama fallback.
    config = _config(
        {
            "generator": {
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "fallback": {"provider": "ollama", "model": "qwen2.5:7b-instruct"},
            }
        }
    )
    registry = ModelRegistry(config, _settings())
    model = registry.chat_model("generator")
    assert isinstance(model, BaseChatModel)  # the fallback built successfully


def test_no_fallback_reraises_actionably() -> None:
    config = _config({"generator": {"provider": "anthropic", "model": "claude-sonnet-5"}})
    registry = ModelRegistry(config, _settings())
    with pytest.raises(ValueError, match="no fallback is configured"):
        registry.chat_model("generator")


def test_unknown_role_raises() -> None:
    config = _config({"generator": {"provider": "ollama"}})
    registry = ModelRegistry(config, _settings())
    with pytest.raises(ValueError, match="not defined in profile"):
        registry.chat_model("verifier")


def test_profile_selected_from_settings() -> None:
    config = ModelsConfig.model_validate(
        {
            "default_profile": "local",
            "profiles": {
                "local": {"generator": {"provider": "ollama"}},
                "hosted": {"generator": {"provider": "ollama", "model": "other"}},
            },
        }
    )
    registry = ModelRegistry(config, _settings(models_profile="hosted"))
    assert registry.profile == "hosted"
