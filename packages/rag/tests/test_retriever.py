"""Retriever: dense search ordering, top_k trimming, and the rerank seam."""

from __future__ import annotations

from twin_observability import StepEvent
from twin_rag.models import Chunk, EmbeddedChunk, ScoredChunk
from twin_rag.retriever import NoOpReranker, Retriever
from twin_rag.testing import HashEmbedder, MemoryVectorStore


def _store_with_scores(scores: dict[str, list[float]]) -> MemoryVectorStore:
    """Seed a store with explicit embeddings so similarity scores are controllable."""
    store = MemoryVectorStore()
    for cid, vec in scores.items():
        chunk = Chunk(id=cid, doc_id="d", source_id="s", title=cid, ordinal=0, text=cid)
        store.upsert([EmbeddedChunk(chunk=chunk, embedding=vec)])
    return store


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


def _fixed_query_embedder(vector: list[float]) -> HashEmbedder:
    """A HashEmbedder whose query vector is pinned, so store scores are deterministic."""
    embedder = HashEmbedder(dim=len(vector))
    embedder.embed_query = lambda _text: vector  # type: ignore[method-assign,assignment]
    return embedder


def test_min_score_drops_low_scoring_chunks() -> None:
    # Against query [1,0]: exact=1.0, mid=0.6, orthogonal=0.0 (dot of unit vectors).
    store = _store_with_scores({"exact": [1.0, 0.0], "mid": [0.6, 0.8], "orthogonal": [0.0, 1.0]})
    retriever = Retriever(_fixed_query_embedder([1.0, 0.0]), store, top_k=5, min_score=0.5)
    kept = retriever.retrieve("q")
    assert {c.chunk.id for c in kept} == {"exact", "mid"}


def test_retrieve_returns_empty_when_all_below_floor() -> None:
    store = _store_with_scores({"a": [0.0, 1.0], "b": [0.1, 0.99]})
    retriever = Retriever(_fixed_query_embedder([1.0, 0.0]), store, top_k=5, min_score=0.5)

    events: list[StepEvent] = []
    result = retriever.retrieve("anything", sink=events.append)
    assert result == []
    assert any("relevance floor" in e.message for e in events)
