"""Compose pipelines from settings — the single wiring point for CLI and API.

Keeping construction here (rather than in the CLI and the lifespan separately) means the
server and the ``twin`` CLI build the exact same objects from the exact same config.
Models come from the role-based :class:`~twin_rag.ModelRegistry` (``models.yaml``), so the
generator and embedder are a config choice, not a code change.
"""

from __future__ import annotations

from dataclasses import dataclass

from twin_config import Settings, load_models_config
from twin_rag import (
    AnswerPipeline,
    IngestPipeline,
    ModelRegistry,
    Retriever,
    VectorStore,
    get_vector_store,
    load_sources,
)


def build_registry(settings: Settings) -> ModelRegistry:
    """Build the model registry for the configured profile in ``models.yaml``."""
    config = load_models_config(settings.models_config_path)
    return ModelRegistry(config, settings)


def build_ingest_pipeline(
    settings: Settings,
    *,
    registry: ModelRegistry | None = None,
    store: VectorStore | None = None,
) -> IngestPipeline:
    """Build an :class:`~twin_rag.IngestPipeline` from configuration."""
    registry = registry or build_registry(settings)
    return IngestPipeline(
        load_sources(settings.sources_config_path),
        registry.embedder(),
        store or get_vector_store(settings),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def build_answer_pipeline(
    settings: Settings,
    *,
    registry: ModelRegistry | None = None,
    store: VectorStore | None = None,
) -> AnswerPipeline:
    """Build an :class:`~twin_rag.AnswerPipeline` from configuration."""
    registry = registry or build_registry(settings)
    retriever = Retriever(
        registry.embedder(),
        store or get_vector_store(settings),
        top_k=settings.retrieval_top_k,
    )
    return AnswerPipeline(retriever, registry.chat_model("generator"))


@dataclass
class Backend:
    """The long-lived objects the API keeps on ``app.state`` for the process lifetime."""

    store: VectorStore
    ingest_pipeline: IngestPipeline
    answer_pipeline: AnswerPipeline


def build_backend(settings: Settings) -> Backend:
    """Build everything the API serves, sharing one registry and store across pipelines."""
    registry = build_registry(settings)
    store = get_vector_store(settings)
    return Backend(
        store=store,
        ingest_pipeline=build_ingest_pipeline(settings, registry=registry, store=store),
        answer_pipeline=build_answer_pipeline(settings, registry=registry, store=store),
    )
