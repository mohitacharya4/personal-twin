"""Citation verification — the anti-hallucination guardrail.

The generator is told to cite claims with ``[n]`` markers pointing at numbered context.
This module checks that every marker actually points at a retrieved chunk: valid markers
become :class:`~twin_rag.models.Citation`s, and *dangling* markers (``[7]`` when only 5
chunks were retrieved — the classic sign of a model citing something it invented) are
stripped from the text and reported so the caller can surface or act on them.
"""

from __future__ import annotations

import re

from twin_rag.models import Citation, ScoredChunk

_MARKER = re.compile(r"\[(\d+)\]")


class CitationResult:
    """The outcome of verifying an answer's citations."""

    def __init__(
        self, text: str, citations: list[Citation], unsupported_markers: list[int]
    ) -> None:
        self.text = text
        self.citations = citations
        self.unsupported_markers = unsupported_markers


def verify_citations(text: str, contexts: list[ScoredChunk]) -> CitationResult:
    """Validate ``[n]`` markers in ``text`` against the retrieved ``contexts``.

    Returns the cleaned text (dangling markers removed), the verified citations in marker
    order, and the list of unsupported marker numbers that were removed.
    """
    valid_range = range(1, len(contexts) + 1)
    referenced = [int(m) for m in _MARKER.findall(text)]
    unsupported = sorted({n for n in referenced if n not in valid_range})

    cleaned = _strip_dangling(text, valid_range)

    used = sorted({n for n in referenced if n in valid_range})
    citations = [_citation_for(n, contexts[n - 1]) for n in used]
    return CitationResult(cleaned, citations, unsupported)


def _strip_dangling(text: str, valid_range: range) -> str:
    """Remove markers that point nowhere; tidy the whitespace the removal leaves behind."""

    def replace(match: re.Match[str]) -> str:
        n = int(match.group(1))
        return match.group(0) if n in valid_range else ""

    cleaned = _MARKER.sub(replace, text)
    cleaned = re.sub(r" +([.,;:])", r"\1", cleaned)  # " ." -> "."
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _citation_for(marker: int, scored: ScoredChunk) -> Citation:
    chunk = scored.chunk
    return Citation(
        marker=marker,
        chunk_id=chunk.id,
        title=chunk.title,
        source_id=chunk.source_id,
        uri=chunk.metadata.get("uri"),
    )
