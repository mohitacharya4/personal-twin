"""The ``VectorStore`` port — a pure vector index over chunks.

Embeddings are computed by the pipeline (via :func:`~twin_rag.embeddings.get_embedder`)
and passed in as vectors, so the store stays provider-agnostic: swapping Chroma for
pgvector is a config change behind this one interface. Implementations must treat
``upsert`` as idempotent keyed on :attr:`~twin_rag.models.Chunk.id`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from twin_rag.models import EmbeddedChunk, ScoredChunk


@runtime_checkable
class VectorStore(Protocol):
    """A persistent nearest-neighbour index over embedded chunks."""

    def upsert(self, records: list[EmbeddedChunk]) -> None:
        """Insert or replace chunks by id. Safe to call repeatedly (idempotent)."""
        ...

    def similarity_search(
        self,
        embedding: list[float],
        *,
        k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Return the ``k`` nearest chunks to ``embedding``, most similar first.

        ``where`` optionally filters on chunk metadata (e.g. ``{"source_id": "x"}``).
        """
        ...

    def count(self) -> int:
        """Number of chunks currently indexed."""
        ...

    def reset(self) -> None:
        """Drop everything in the collection (full rebuild)."""
        ...
