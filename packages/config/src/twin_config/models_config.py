"""Typed view of ``models.yaml`` — the role → provider mapping.

Pure configuration: this module parses and validates the file but builds no models
(that would pull LLM SDKs into the config package). The registry that turns a role into a
live model lives in ``twin_rag`` (:class:`twin_rag.registry.ModelRegistry`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ModelsConfigError(ValueError):
    """Raised when ``models.yaml`` is missing, malformed, or names an unknown profile."""


class ModelRef(BaseModel):
    """A minimal provider+model pointer (used for fallbacks)."""

    model_config = ConfigDict(frozen=True)
    provider: str
    model: str | None = None


class RoleSpec(BaseModel):
    """How one role (generator, embedder, verifier, reranker) is served in a profile."""

    model_config = ConfigDict(frozen=True)
    provider: str
    model: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    fallback: ModelRef | None = None

    @property
    def is_none(self) -> bool:
        """True for the reserved ``provider: none`` no-op (e.g. the reranker seam)."""
        return self.provider == "none"

    @property
    def temperature(self) -> float:
        """Sampling temperature from ``params``, defaulting to a low, stable value."""
        value = self.params.get("temperature", 0.1)
        return float(value)


class ModelsConfig(BaseModel):
    """The whole parsed ``models.yaml``."""

    model_config = ConfigDict(frozen=True)
    default_profile: str
    profiles: dict[str, dict[str, RoleSpec]]
    budgets: dict[str, Any] = Field(default_factory=dict)

    def profile(self, name: str | None = None) -> dict[str, RoleSpec]:
        """Return the named profile (or the default). Raises if it is not defined."""
        chosen = name or self.default_profile
        if chosen not in self.profiles:
            known = ", ".join(sorted(self.profiles))
            msg = f"unknown models profile {chosen!r} (known: {known})"
            raise ModelsConfigError(msg)
        return self.profiles[chosen]


def load_models_config(path: Path) -> ModelsConfig:
    """Parse and validate ``models.yaml`` at ``path``."""
    if not path.exists():
        msg = f"models config not found: {path}"
        raise ModelsConfigError(msg)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        config = ModelsConfig.model_validate(raw)
    except Exception as exc:
        msg = f"invalid models config {path}: {exc}"
        raise ModelsConfigError(msg) from exc
    # Fail fast if the default profile is itself undefined.
    config.profile(config.default_profile)
    return config
