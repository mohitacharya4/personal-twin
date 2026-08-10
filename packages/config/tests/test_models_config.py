"""Parsing and validating models.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest
from twin_config import ModelsConfigError, load_models_config

_YAML = """
default_profile: local
profiles:
  local:
    generator:
      provider: ollama
      model: qwen2.5:7b-instruct
      params: { temperature: 0.2 }
      fallback: null
    reranker:
      provider: none
      model: null
      params: {}
  hosted:
    generator:
      provider: anthropic
      model: claude-sonnet-5
      params: { temperature: 0 }
      fallback: { provider: ollama, model: qwen2.5:7b-instruct }
budgets:
  request_timeout_seconds: 60
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_parses_profiles_and_roles(tmp_path: Path) -> None:
    config = load_models_config(_write(tmp_path, _YAML))
    local = config.profile("local")
    assert local["generator"].provider == "ollama"
    assert local["generator"].temperature == 0.2
    assert local["reranker"].is_none is True


def test_default_profile_and_fallback(tmp_path: Path) -> None:
    config = load_models_config(_write(tmp_path, _YAML))
    default = config.profile()  # default_profile == local
    assert default["generator"].fallback is None
    hosted = config.profile("hosted")
    assert hosted["generator"].fallback is not None
    assert hosted["generator"].fallback.provider == "ollama"


def test_unknown_profile_raises(tmp_path: Path) -> None:
    config = load_models_config(_write(tmp_path, _YAML))
    with pytest.raises(ModelsConfigError, match="unknown models profile"):
        config.profile("gpu-cluster")


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ModelsConfigError, match="not found"):
        load_models_config(tmp_path / "absent.yaml")


def test_temperature_defaults_when_absent(tmp_path: Path) -> None:
    config = load_models_config(_write(tmp_path, _YAML))
    # reranker has no params.temperature -> the safe default.
    assert config.profile("local")["reranker"].temperature == 0.1
