"""Deterministic eval metrics — the CI-safe scoring core."""

from __future__ import annotations

from twin_rag.evals.metrics import (
    EvalCase,
    citation_validity,
    context_recall,
    groundedness,
    keyword_recall,
    score_answer,
)
from twin_rag.models import Answer, Chunk, Citation, ScoredChunk


def _context(title: str, text: str, uri: str) -> ScoredChunk:
    return ScoredChunk(
        chunk=Chunk(
            id=title,
            doc_id="d",
            source_id="s",
            title=title,
            ordinal=0,
            text=text,
            metadata={"uri": uri},
        ),
        score=0.9,
    )


def test_keyword_recall() -> None:
    assert keyword_recall("I value tests and tracing.", ["tests", "tracing"]) == 1.0
    assert keyword_recall("I value tests.", ["tests", "tracing"]) == 0.5
    assert keyword_recall("anything", []) == 1.0


def test_citation_validity() -> None:
    good = Answer(
        text="x [1]", citations=[Citation(marker=1, chunk_id="c", title="t", source_id="s")]
    )
    assert citation_validity(good) == 1.0

    half = Answer(
        text="x [1]",
        citations=[Citation(marker=1, chunk_id="c", title="t", source_id="s")],
        unsupported_markers=[9],
    )
    assert citation_validity(half) == 0.5

    # Nothing to validate -> perfect (an honest no-knowledge answer).
    assert citation_validity(Answer(text="I don't know.")) == 1.0


def test_context_recall_matches_uri_or_title() -> None:
    answer = Answer(text="a", contexts=[_context("Values", "body", "values.md")])
    assert context_recall(answer, ["values.md"]) == 1.0
    assert context_recall(answer, ["Values"]) == 1.0
    assert context_recall(answer, ["values.md", "missing.md"]) == 0.5
    assert context_recall(answer, []) == 1.0


def test_groundedness_rewards_overlap_penalises_drift() -> None:
    ctx = _context("Values", "observability tests reliability tracing", "v.md")
    grounded = Answer(text="observability and tracing matter", contexts=[ctx])
    drifted = Answer(text="quantum blockchain synergy paradigm", contexts=[ctx])
    assert groundedness(grounded) > groundedness(drifted)
    # No context to ground against -> 0.0 for a content-bearing answer.
    assert groundedness(Answer(text="some words")) == 0.0


def test_score_answer_aggregates() -> None:
    ctx = _context("Values", "I value tests and observability", "values.md")
    answer = Answer(
        text="I value tests [1]",
        citations=[Citation(marker=1, chunk_id="Values", title="Values", source_id="s")],
        contexts=[ctx],
    )
    case = EvalCase(question="What do you value?", keywords=["tests"], must_cite=["values.md"])
    scores = score_answer(answer, case)
    assert scores.keyword_recall == 1.0
    assert scores.citation_validity == 1.0
    assert scores.context_recall == 1.0
    assert scores.groundedness > 0.0
