"""Factory guard rails: clear, actionable errors for misconfiguration."""

from __future__ import annotations

import pytest
from twin_config import Settings
from twin_rag.embeddings import get_embedder
from twin_rag.llm import get_llm
from twin_rag.vectorstore.factory import get_vector_store


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg,arg-type]


def test_get_llm_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm(provider="grok", settings=_settings())  # type: ignore[arg-type]


def test_get_llm_anthropic_without_key_is_actionable() -> None:
    with pytest.raises(ValueError, match="TWIN_ANTHROPIC_API_KEY"):
        get_llm(provider="anthropic", settings=_settings())


def test_get_embedder_openai_without_key_is_actionable() -> None:
    with pytest.raises(ValueError, match="TWIN_OPENAI_API_KEY"):
        get_embedder(provider="openai", settings=_settings())


def test_get_embedder_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedder(provider="word2vec", settings=_settings())  # type: ignore[arg-type]


def test_vector_store_pgvector_without_dsn_is_actionable() -> None:
    with pytest.raises(ValueError, match="TWIN_DATABASE_URL"):
        get_vector_store(_settings(vector_store_backend="pgvector"))
