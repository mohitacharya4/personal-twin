"""Deterministic RAG metrics — no model required, so they run in CI.

These score a produced :class:`~twin_rag.models.Answer` against a labelled case. They are
intentionally simple and explainable (lexical, set-based) rather than model-judged: the
LLM-as-judge rubric lives in the eval runner, where a live model is available. Keeping the
deterministic core here means scoring logic is unit-tested even when full runs need Ollama.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from twin_rag.models import Answer

# A tiny stopword set so groundedness measures content-word overlap, not "the/a/is".
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have i in is it its of on or that the to was "
    "with you your my me we our".split()
)

_WORD = re.compile(r"[a-z0-9]+")


class EvalCase(BaseModel):
    """One labelled evaluation example."""

    question: str
    keywords: list[str] = []
    #: Source identifiers (uri or title) retrieval is expected to surface for this question.
    must_cite: list[str] = []
    answer_gist: str | None = None


def _tokens(text: str, *, drop_stopwords: bool = False) -> set[str]:
    toks = set(_WORD.findall(text.lower()))
    return {t for t in toks if t not in _STOPWORDS} if drop_stopwords else toks


def keyword_recall(answer_text: str, keywords: list[str]) -> float:
    """Fraction of expected keywords/phrases present in the answer (case-insensitive)."""
    if not keywords:
        return 1.0
    haystack = answer_text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in haystack)
    return hits / len(keywords)


def citation_validity(answer: Answer) -> float:
    """Share of the answer's citation markers that point at a real retrieved context.

    1.0 when there is nothing to validate (e.g. an honest "no information" answer).
    """
    total = len(answer.citations) + len(answer.unsupported_markers)
    if total == 0:
        return 1.0
    return len(answer.citations) / total


def context_recall(answer: Answer, must_cite: list[str]) -> float:
    """Fraction of expected sources that appear among the retrieved contexts."""
    if not must_cite:
        return 1.0
    retrieved: set[str] = set()
    for scored in answer.contexts:
        retrieved.add(scored.chunk.title.lower())
        uri = scored.chunk.metadata.get("uri")
        if isinstance(uri, str):
            retrieved.add(uri.lower())
    hits = sum(1 for expected in must_cite if expected.lower() in retrieved)
    return hits / len(must_cite)


def groundedness(answer: Answer) -> float:
    """Lexical overlap of the answer's content words with its retrieved contexts.

    A cheap faithfulness proxy: an answer built from the context scores high; one that
    drifts into outside knowledge scores low. Undefined (1.0) when there is no context and
    no answer content to ground.
    """
    context_tokens: set[str] = set()
    for scored in answer.contexts:
        context_tokens |= _tokens(scored.chunk.text, drop_stopwords=True)

    answer_tokens = _tokens(answer.text, drop_stopwords=True)
    if not answer_tokens:
        return 1.0
    if not context_tokens:
        return 0.0
    return len(answer_tokens & context_tokens) / len(answer_tokens)


class Scores(BaseModel):
    """Deterministic scores for one answered case (each in ``[0, 1]``)."""

    keyword_recall: float
    citation_validity: float
    context_recall: float
    groundedness: float


def score_answer(answer: Answer, case: EvalCase) -> Scores:
    """Compute every deterministic metric for one answered case."""
    return Scores(
        keyword_recall=keyword_recall(answer.text, case.keywords),
        citation_validity=citation_validity(answer),
        context_recall=context_recall(answer, case.must_cite),
        groundedness=groundedness(answer),
    )
