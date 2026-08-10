"""Provider-agnostic embedding-model factory.

The pipeline talks to ``get_embedder()`` and never imports a concrete provider, so the
embedding backend is a config choice, not a code change. The returned object is always a
LangChain ``Embeddings``, so ``.embed_documents()`` / ``.embed_query()`` behave the same
downstream.

⚠️  Changing the embedder is a **migration**, not a tweak: vectors from different models
live in different spaces and must not be mixed in one store. Re-ingest into a fresh
collection after switching.
"""

from __future__ import annotations

from typing import Literal, cast

from langchain_core.embeddings import Embeddings
from twin_config import Settings, get_settings

EmbeddingProvider = Literal["ollama", "openai"]

DEFAULT_OLLAMA_EMBED_MODEL = "nomic-embed-text"
DEFAULT_OPENAI_EMBED_MODEL = "text-embedding-3-small"


def get_embedder(
    *,
    provider: EmbeddingProvider = "ollama",
    model: str | None = None,
    settings: Settings | None = None,
) -> Embeddings:
    """Build an embedding model for the requested provider.

    Args:
        provider: Which backend to use. Anthropic is intentionally absent — it exposes
            no embeddings API; pair an Anthropic generator with an Ollama/OpenAI embedder.
        model: Override the provider's default embedding model.
        settings: Injected settings (defaults to the cached process settings).
    """
    settings = settings or get_settings()
    if provider == "ollama":
        return _build_ollama(settings, model)
    if provider == "openai":
        return _build_openai(settings, model)
    raise ValueError(f"Unknown embedding provider: {provider!r}")


def _build_ollama(settings: Settings, model: str | None) -> Embeddings:
    from langchain_ollama import OllamaEmbeddings

    embedder = OllamaEmbeddings(
        model=model or DEFAULT_OLLAMA_EMBED_MODEL,
        base_url=settings.ollama_base_url,
    )
    return cast(Embeddings, embedder)


def _build_openai(settings: Settings, model: str | None) -> Embeddings:
    if not settings.openai_api_key:
        raise ValueError(
            "Embedding provider 'openai' requires TWIN_OPENAI_API_KEY. "
            "Set it in .env or use the 'ollama' embedder."
        )
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "The 'openai' extra is not installed. Run: uv sync --extra openai"
        ) from exc

    embedder = OpenAIEmbeddings(
        model=model or DEFAULT_OPENAI_EMBED_MODEL,
        api_key=settings.openai_api_key,
    )
    return cast(Embeddings, embedder)
