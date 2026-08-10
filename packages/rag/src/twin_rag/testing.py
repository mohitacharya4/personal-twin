"""Deterministic, offline test doubles for the RAG stages.

Public so both the ``twin_rag`` unit tests and the API tests can build a real pipeline
without a live model or network — a fake embedder, an in-memory store, a list-backed
source, and a canned chat model. Import from here; do not re-implement per test suite.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from twin_rag.models import EmbeddedChunk, RawDocument, ScoredChunk, SourceRef


class HashEmbedder(Embeddings):
    """A tiny, deterministic embedder — no model, no network.

    Maps text to a fixed-width bag-of-characters vector. Good enough for exercising
    wiring and nearest-neighbour ordering without pulling in Ollama.
    """

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for char in text.lower():
            vec[ord(char) % self.dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class MemoryVectorStore:
    """An in-memory :class:`~twin_rag.vectorstore.base.VectorStore` for tests."""

    def __init__(self) -> None:
        self.records: dict[str, EmbeddedChunk] = {}

    def upsert(self, records: list[EmbeddedChunk]) -> None:
        for record in records:
            self.records[record.chunk.id] = record

    def similarity_search(
        self, embedding: list[float], *, k: int, where: Mapping[str, Any] | None = None
    ) -> list[ScoredChunk]:
        def dot(a: list[float], b: list[float]) -> float:
            return sum(x * y for x, y in zip(a, b, strict=True))

        candidates = [
            rec
            for rec in self.records.values()
            if where is None or all(getattr(rec.chunk, key) == val for key, val in where.items())
        ]
        ranked = sorted(candidates, key=lambda r: dot(embedding, r.embedding), reverse=True)
        return [ScoredChunk(chunk=r.chunk, score=dot(embedding, r.embedding)) for r in ranked[:k]]

    def count(self) -> int:
        return len(self.records)

    def reset(self) -> None:
        self.records.clear()


class ListSource:
    """A :class:`~twin_rag.sources.base.DocumentSource` backed by in-memory documents."""

    def __init__(self, source_id: str, docs: dict[str, str]) -> None:
        self._id = source_id
        self._docs = docs

    @property
    def id(self) -> str:
        return self._id

    def list_all(self) -> Iterable[SourceRef]:
        for uri in self._docs:
            yield SourceRef(source_id=self._id, uri=uri, title=uri)

    def fetch(self, ref: SourceRef) -> RawDocument:
        return RawDocument(ref=ref, text=self._docs[ref.uri])


def make_fake_chat_model(response: str) -> BaseChatModel:
    """A chat model that always returns ``response`` — for testing the generation path."""
    return FakeMessagesListChatModel(responses=[AIMessage(content=response)])
