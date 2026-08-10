"""The Chroma backend upserts, searches by similarity, counts, and resets.

Uses a real (embedded, on-disk) Chroma with precomputed vectors — no model, no network —
so it exercises the actual backend rather than a mock.
"""

from __future__ import annotations

from pathlib import Path

from twin_rag.models import Chunk, EmbeddedChunk
from twin_rag.vectorstore.chroma import ChromaVectorStore


def _chunk(cid: str, text: str, *, source_id: str = "s") -> Chunk:
    return Chunk(
        id=cid,
        doc_id="d",
        source_id=source_id,
        title="t",
        ordinal=0,
        text=text,
        metadata={"uri": f"{cid}.md"},
    )


def _store(tmp_path: Path) -> ChromaVectorStore:
    return ChromaVectorStore(tmp_path / "chroma")


def test_upsert_and_search_orders_by_similarity(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        [
            EmbeddedChunk(chunk=_chunk("near", "near"), embedding=[1.0, 0.0]),
            EmbeddedChunk(chunk=_chunk("far", "far"), embedding=[0.0, 1.0]),
        ]
    )
    results = store.similarity_search([1.0, 0.0], k=2)
    assert [r.chunk.id for r in results] == ["near", "far"]
    assert results[0].score > results[1].score
    assert results[0].chunk.metadata["uri"] == "near.md"


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = EmbeddedChunk(chunk=_chunk("x", "hello"), embedding=[0.3, 0.7])
    store.upsert([record])
    store.upsert([record])
    assert store.count() == 1


def test_where_filter_restricts_by_metadata(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        [
            EmbeddedChunk(chunk=_chunk("a", "a", source_id="one"), embedding=[1.0, 0.0]),
            EmbeddedChunk(chunk=_chunk("b", "b", source_id="two"), embedding=[0.9, 0.1]),
        ]
    )
    results = store.similarity_search([1.0, 0.0], k=5, where={"source_id": "two"})
    assert [r.chunk.id for r in results] == ["b"]


def test_reset_empties_the_collection(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert([EmbeddedChunk(chunk=_chunk("x", "hi"), embedding=[1.0, 0.0])])
    assert store.count() == 1
    store.reset()
    assert store.count() == 0
