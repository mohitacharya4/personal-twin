"""Resolve a role to a live model — the bridge from ``models.yaml`` to real providers.

Code asks the registry for a *role* ("generator", "embedder"); the registry looks up the
active profile, builds the configured provider via :func:`~twin_rag.llm.get_llm` /
:func:`~twin_rag.embeddings.get_embedder`, and — if that provider can't be built (missing
key or extra) — falls back to the role's declared fallback instead of crashing.

Per-request runtime failover (retry the fallback when a live call errors) is a planned
enhancement; today fallback resolves at construction time, which already lets a profile
degrade gracefully when a provider isn't configured.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from twin_config import ModelRef, ModelsConfig, RoleSpec, Settings
from twin_observability import get_logger

from twin_rag.embeddings import EmbeddingProvider, get_embedder
from twin_rag.llm import LLMProvider, get_llm

log = get_logger(__name__)


class ModelRegistry:
    """Build models for roles from a resolved ``models.yaml`` profile."""

    def __init__(
        self, config: ModelsConfig, settings: Settings, *, profile: str | None = None
    ) -> None:
        self._settings = settings
        self._profile_name = profile or settings.models_profile or config.default_profile
        self._roles = config.profile(self._profile_name)

    @property
    def profile(self) -> str:
        return self._profile_name

    def _spec(self, role: str) -> RoleSpec:
        spec = self._roles.get(role)
        if spec is None:
            known = ", ".join(sorted(self._roles))
            msg = f"role {role!r} not defined in profile {self._profile_name!r} (roles: {known})"
            raise ValueError(msg)
        return spec

    def chat_model(self, role: str) -> BaseChatModel:
        """Build the chat model for ``role`` (e.g. 'generator', 'verifier')."""
        spec = self._spec(role)
        try:
            return get_llm(
                provider=_as_llm_provider(spec.provider),
                model=spec.model,
                temperature=spec.temperature,
                settings=self._settings,
            )
        except (ValueError, ImportError) as exc:
            fallback = self._require_fallback(role, spec, exc)
            log.warning("registry.fallback", role=role, to=fallback.provider)
            return get_llm(
                provider=_as_llm_provider(fallback.provider),
                model=fallback.model,
                temperature=spec.temperature,
                settings=self._settings,
            )

    def embedder(self, role: str = "embedder") -> Embeddings:
        """Build the embedding model for ``role`` (default 'embedder')."""
        spec = self._spec(role)
        try:
            return get_embedder(
                provider=_as_embedding_provider(spec.provider),
                model=spec.model,
                settings=self._settings,
            )
        except (ValueError, ImportError) as exc:
            fallback = self._require_fallback(role, spec, exc)
            log.warning("registry.fallback", role=role, to=fallback.provider)
            return get_embedder(
                provider=_as_embedding_provider(fallback.provider),
                model=fallback.model,
                settings=self._settings,
            )

    @staticmethod
    def _require_fallback(role: str, spec: RoleSpec, exc: Exception) -> ModelRef:
        if spec.fallback is None:
            msg = (
                f"cannot build role {role!r} ({spec.provider}) and no fallback is configured: {exc}"
            )
            raise ValueError(msg) from exc
        return spec.fallback


def _as_llm_provider(name: str) -> LLMProvider:
    if name not in ("ollama", "anthropic", "openai"):
        msg = f"unknown chat provider in models.yaml: {name!r}"
        raise ValueError(msg)
    return name  # type: ignore[return-value]  # narrowed by the guard above


def _as_embedding_provider(name: str) -> EmbeddingProvider:
    if name not in ("ollama", "openai"):
        msg = f"unknown embedding provider in models.yaml: {name!r}"
        raise ValueError(msg)
    return name  # type: ignore[return-value]  # narrowed by the guard above
