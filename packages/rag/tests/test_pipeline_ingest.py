"""The ingest pipeline: fetch -> chunk -> embed -> upsert, with events and selection."""

from __future__ import annotations

from twin_observability import StepEvent
from twin_rag.pipeline import IngestPipeline
from twin_rag.testing import HashEmbedder, ListSource, MemoryVectorStore


def _pipeline(*sources: ListSource) -> tuple[IngestPipeline, MemoryVectorStore]:
    store = MemoryVectorStore()
    pipeline = IngestPipeline(
        sources, HashEmbedder(), store, chunk_size=60, chunk_overlap=0, embed_batch_size=2
    )
    return pipeline, store


def test_run_indexes_all_sources() -> None:
    docs = {"a.md": "First paragraph.\n\nSecond paragraph here.", "b.md": "Another document."}
    pipeline, store = _pipeline(ListSource("docs", docs))

    report = pipeline.run()

    assert report.documents == 2
    assert report.chunks == store.count() > 0
    assert report.per_source["docs"] == store.count()


def test_run_emits_step_events() -> None:
    pipeline, _ = _pipeline(ListSource("docs", {"a.md": "Hello world."}))
    events: list[StepEvent] = []
    pipeline.run(sink=events.append)
    nodes = {e.node for e in events}
    assert {"ingest", "embed"} <= nodes
    assert any(e.phase == "complete" for e in events)


def test_source_selection_filters() -> None:
    pipeline, store = _pipeline(
        ListSource("keep", {"a.md": "Keep this."}),
        ListSource("skip", {"b.md": "Skip this."}),
    )
    report = pipeline.run(source_id="keep")
    assert set(report.per_source) == {"keep"}
    assert store.count() == report.chunks


def test_unknown_source_id_raises() -> None:
    pipeline, _ = _pipeline(ListSource("docs", {"a.md": "x"}))
    try:
        pipeline.run(source_id="ghost")
    except ValueError as exc:
        assert "ghost" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_reset_clears_before_indexing() -> None:
    pipeline, store = _pipeline(ListSource("docs", {"a.md": "Hello."}))
    pipeline.run()
    before = store.count()
    pipeline.run(reset=True)
    assert store.count() == before  # same content re-indexed, not duplicated
