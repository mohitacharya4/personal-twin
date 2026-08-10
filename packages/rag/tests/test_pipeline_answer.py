"""The answer pipeline: retrieve -> generate -> verify, end to end with fakes."""

from __future__ import annotations

from twin_observability import StepEvent
from twin_rag.models import Chunk, EmbeddedChunk
from twin_rag.pipeline import AnswerPipeline
from twin_rag.retriever import Retriever
from twin_rag.testing import HashEmbedder, MemoryVectorStore, make_fake_chat_model


def _seed_store() -> MemoryVectorStore:
    store, embedder = MemoryVectorStore(), HashEmbedder()
    chunk = Chunk(
        id="c1",
        doc_id="d",
        source_id="personal",
        title="Values",
        ordinal=0,
        text="I value observability and tests.",
        metadata={"uri": "values.md"},
    )
    store.upsert([EmbeddedChunk(chunk=chunk, embedding=embedder.embed_query(chunk.text))])
    return store


def _pipeline(store: MemoryVectorStore, response: str) -> AnswerPipeline:
    retriever = Retriever(HashEmbedder(), store, top_k=3)
    return AnswerPipeline(retriever, make_fake_chat_model(response))


def test_answer_is_grounded_and_cited() -> None:
    pipeline = _pipeline(_seed_store(), "I value observability and tests [1].")
    answer = pipeline.run("What do you value?")

    assert "[1]" in answer.text
    assert [c.marker for c in answer.citations] == [1]
    assert answer.citations[0].title == "Values"
    assert answer.unsupported_markers == []
    assert len(answer.contexts) == 1


def test_dangling_citation_is_stripped() -> None:
    pipeline = _pipeline(_seed_store(), "Grounded [1]. Hallucinated [4].")
    answer = pipeline.run("What do you value?")
    assert answer.unsupported_markers == [4]
    assert "[4]" not in answer.text


def test_empty_store_returns_no_knowledge_answer() -> None:
    pipeline = _pipeline(MemoryVectorStore(), "should not be used")
    answer = pipeline.run("Anything?")
    assert "don't have information" in answer.text
    assert answer.citations == []


def test_run_emits_stage_events() -> None:
    pipeline = _pipeline(_seed_store(), "Answer [1].")
    events: list[StepEvent] = []
    pipeline.run("What do you value?", sink=events.append)
    nodes = {e.node for e in events}
    assert {"answer", "retrieve", "generate", "verify"} <= nodes
