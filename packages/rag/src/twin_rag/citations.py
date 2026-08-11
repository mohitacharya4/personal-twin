"""Citation verification — the anti-hallucination guardrail.

The generator is told to cite claims with ``[n]`` markers pointing at numbered context.
This module checks that every marker actually points at a retrieved chunk: valid markers
become :class:`~twin_rag.models.Citation`s, and *dangling* markers (``[7]`` when only 5
chunks were retrieved — the classic sign of a model citing something it invented) are
stripped from the text and reported so the caller can surface or act on them.

Grouped markers are normalised too: models routinely write ``[1, 3]`` for two sources, so
we expand those to ``[1][3]`` — the single-marker form every consumer (the SSE stream, the
UI) already understands — keeping only the numbers that resolve.
"""

from __future__ import annotations

import re

from twin_rag.models import Citation, ScoredChunk

# One or more comma-separated numbers inside a single bracket: [1], [1,3], [1, 2, 4].
_GROUP = re.compile(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]")


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

    Returns the normalised text (grouped markers split, dangling markers removed), the
    verified citations in first-appearance order, and the unsupported marker numbers.
    """
    valid_range = range(1, len(contexts) + 1)
    used: list[int] = []
    unsupported: set[int] = set()

    def replace(match: re.Match[str]) -> str:
        valid: list[int] = []
        for raw in match.group(1).split(","):
            n = int(raw)
            if n in valid_range:
                valid.append(n)
                if n not in used:
                    used.append(n)
            else:
                unsupported.add(n)
        return "".join(f"[{n}]" for n in valid)  # dangling numbers dropped

    cleaned = _tidy(_GROUP.sub(replace, text))
    citations = [_citation_for(n, contexts[n - 1]) for n in used]
    return CitationResult(cleaned, citations, sorted(unsupported))


def _tidy(text: str) -> str:
    """Tidy whitespace left where markers were removed (e.g. ``Invented .`` -> ``Invented.``)."""
    text = re.sub(r" +([.,;:])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _citation_for(marker: int, scored: ScoredChunk) -> Citation:
    chunk = scored.chunk
    return Citation(
        marker=marker,
        chunk_id=chunk.id,
        title=chunk.title,
        source_id=chunk.source_id,
        uri=chunk.metadata.get("uri"),
    )
