"""The data that flows through the pipeline.

One document becomes many :class:`Chunk`s; each chunk is embedded into an
:class:`EmbeddedChunk` for storage and comes back from search as a :class:`ScoredChunk`.
Every model is immutable so a chunk's identity and provenance can't drift between stages.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceRef(BaseModel):
    """A pointer to one document within a source, before its content is fetched."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(description="Owning source, e.g. 'personal-docs'")
    uri: str = Field(description="Locator within the source, e.g. a file path or URL")
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        """Stable, source-scoped document id (``<source_id>:<uri hash>``)."""
        digest = hashlib.sha1(self.uri.encode("utf-8")).hexdigest()[:16]  # noqa: S324 — id, not crypto
        return f"{self.source_id}:{digest}"


class RawDocument(BaseModel):
    """A fetched document's plain text plus the metadata worth carrying to answers."""

    model_config = ConfigDict(frozen=True)

    ref: SourceRef
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A retrievable unit of one document, with enough provenance to cite it."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Deterministic id: stable across re-ingests of identical content")
    doc_id: str
    source_id: str
    title: str
    ordinal: int = Field(description="0-based position of this chunk within its document")
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    """A chunk paired with its embedding vector, ready to upsert into a vector store."""

    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    embedding: list[float]


class ScoredChunk(BaseModel):
    """A chunk returned by retrieval, with the store's similarity score attached."""

    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float = Field(description="Higher is more relevant (cosine similarity)")


class Citation(BaseModel):
    """A source the answer grounded a claim in, addressable by its ``[n]`` marker."""

    model_config = ConfigDict(frozen=True)

    marker: int = Field(description="The 1-based number used in the answer text, e.g. 2 for [2]")
    chunk_id: str
    title: str
    source_id: str
    uri: str | None = None


class Answer(BaseModel):
    """A grounded, citation-verified answer plus the evidence behind it."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="The answer, with only verified [n] markers retained")
    citations: list[Citation] = Field(default_factory=list)
    contexts: list[ScoredChunk] = Field(default_factory=list)
    unsupported_markers: list[int] = Field(
        default_factory=list,
        description="[n] markers the model wrote that pointed at no retrieved context",
    )
    usage: dict[str, Any] = Field(
        default_factory=dict, description="Token accounting, if available"
    )


def make_chunk_id(doc_id: str, ordinal: int, text: str) -> str:
    """Deterministic chunk id.

    Content-addressed on ``(doc_id, ordinal, text)`` so re-ingesting an unchanged
    document upserts the *same* ids (idempotent), while an edit changes the id of only
    the chunks that actually changed.
    """
    payload = f"{doc_id}|{ordinal}|{text}".encode()
    return hashlib.sha1(payload).hexdigest()  # noqa: S324 — content id, not a security hash
