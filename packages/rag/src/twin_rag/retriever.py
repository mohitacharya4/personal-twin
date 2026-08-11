"""Retrieval: embed the query, search the store, then (optionally) rerank.

The rerank stage is a first-class seam. Today the default is :class:`NoOpReranker`,
which passes candidates through unchanged — mirroring the ``reranker: provider: none``
role reserved in ``models.yaml``. Enabling real reranking later is a new
:class:`Reranker` implementation plus an ``over_fetch`` wider than ``top_k``; the
retriever, the pipeline, and the API do not change.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.embeddings import Embeddings
from twin_observability import EventSink, StepEvent

from twin_rag.models import ScoredChunk
from twin_rag.vectorstore.base import VectorStore


@runtime_checkable
class Reranker(Protocol):
    """Re-order (and trim) candidate chunks for a query. The precision stage."""

    def rerank(
        self, query: str, candidates: list[ScoredChunk], *, top_k: int
    ) -> list[ScoredChunk]: ...


class NoOpReranker:
    """Pass-through reranker: keep the vector-store order, trim to ``top_k``."""

    def rerank(self, query: str, candidates: list[ScoredChunk], *, top_k: int) -> list[ScoredChunk]:
        return candidates[:top_k]


class Retriever:
    """Dense retrieval over a :class:`VectorStore`, with a pluggable rerank stage."""

    def __init__(
        self,
        embedder: Embeddings,
        store: VectorStore,
        *,
        top_k: int,
        min_score: float = 0.0,
        over_fetch: int | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k
        self._min_score = min_score
        # With a no-op reranker there is nothing to gain from over-fetching, so default
        # to top_k. A real reranker sets over_fetch > top_k to widen the candidate net.
        self._over_fetch = over_fetch if over_fetch is not None else top_k
        self._reranker = reranker or NoOpReranker()

    def retrieve(self, query: str, *, sink: EventSink | None = None) -> list[ScoredChunk]:
        """Return the most relevant chunks for ``query`` that clear the score floor.

        Returns ``[]`` when nothing clears :attr:`min_score` — the caller treats that as
        an out-of-scope question rather than answering from weak, off-topic context.
        """
        query_vector = self._embedder.embed_query(query)
        candidates = self._store.similarity_search(query_vector, k=self._over_fetch)
        if sink is not None:
            sink(
                StepEvent(
                    node="retrieve",
                    phase="complete",
                    message=f"Retrieved {len(candidates)} candidate chunk(s)",
                    data={"candidates": len(candidates)},
                )
            )
        reranked = self._reranker.rerank(query, candidates, top_k=self._top_k)
        if not isinstance(self._reranker, NoOpReranker) and sink is not None:
            sink(
                StepEvent(
                    node="rerank", phase="complete", message=f"Reranked to top {len(reranked)}"
                )
            )

        # Relevance floor: keep only chunks the store is confident about. When the floor
        # removes everything, the top candidate (if any) explains why in the trace.
        kept = [c for c in reranked if c.score >= self._min_score]
        if not kept and reranked and sink is not None:
            sink(
                StepEvent(
                    node="retrieve",
                    phase="complete",
                    message=(
                        f"No chunk cleared the relevance floor "
                        f"(best {reranked[0].score:.3f} < {self._min_score:.2f})"
                    ),
                    data={"best_score": reranked[0].score, "min_score": self._min_score},
                )
            )
        return kept
