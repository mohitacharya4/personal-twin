"""Retriever: dense search ordering, top_k trimming, and the rerank seam."""

from __future__ import annotations

from twin_rag.models import Chunk, EmbeddedChunk, ScoredChunk
from twin_rag.retriever import NoOpReranker, Retriever
from twin_rag.testing import HashEmbedder, MemoryVectorStore


def _seed(store: MemoryVectorStore, embedder: HashEmbedder, texts: dict[str, str]) -> None:
    for cid, text in texts.items():
        chunk = Chunk(
            id=cid, doc_id="d", source_id="s", title=cid, ordinal=0, text=text, metadata={}
        )
        store.upsert([EmbeddedChunk(chunk=chunk, embedding=embedder.embed_query(text))])


def test_retrieve_returns_top_k_most_similar() -> None:
    store, embedder = MemoryVectorStore(), HashEmbedder()
    _seed(store, embedder, {"cats": "cats and kittens", "code": "python code review", "x": "zzz"})
    retriever = Retriever(embedder, store, top_k=2)

    results = retriever.retrieve("kittens and cats")
    assert len(results) == 2
    assert results[0].chunk.id == "cats"


def test_no_op_reranker_preserves_store_order() -> None:
    reranker = NoOpReranker()
    candidates = [
        ScoredChunk(
            chunk=Chunk(id=str(i), doc_id="d", source_id="s", title="t", ordinal=i, text="x"),
            score=1.0 - i,
        )
        for i in range(5)
    ]
    kept = reranker.rerank("q", candidates, top_k=3)
    assert [c.chunk.id for c in kept] == ["0", "1", "2"]


def test_over_fetch_defaults_to_top_k() -> None:
    store, embedder = MemoryVectorStore(), HashEmbedder()
    _seed(store, embedder, {f"c{i}": f"doc {i}" for i in range(10)})
    retriever = Retriever(embedder, store, top_k=3)
    assert len(retriever.retrieve("doc")) == 3
