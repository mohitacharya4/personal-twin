"""Citation verification: valid markers kept, dangling markers stripped and reported."""

from __future__ import annotations

from twin_rag.citations import verify_citations
from twin_rag.models import Chunk, ScoredChunk


def _contexts(n: int) -> list[ScoredChunk]:
    return [
        ScoredChunk(
            chunk=Chunk(
                id=f"c{i}",
                doc_id="d",
                source_id="s",
                title=f"Doc {i}",
                ordinal=i,
                text=f"content {i}",
                metadata={"uri": f"{i}.md"},
            ),
            score=1.0 - i * 0.1,
        )
        for i in range(1, n + 1)
    ]


def test_valid_markers_become_citations() -> None:
    result = verify_citations("I value tests [1] and tracing [2].", _contexts(3))
    assert result.unsupported_markers == []
    assert [c.marker for c in result.citations] == [1, 2]
    assert result.citations[0].chunk_id == "c1"
    assert result.citations[0].uri == "1.md"
    assert result.text == "I value tests [1] and tracing [2]."


def test_dangling_marker_is_stripped_and_reported() -> None:
    result = verify_citations("Grounded [1]. Invented [9].", _contexts(2))
    assert result.unsupported_markers == [9]
    assert "[9]" not in result.text
    assert "[1]" in result.text
    # Whitespace left by the removed marker is tidied.
    assert "Invented." in result.text


def test_duplicate_markers_yield_one_citation() -> None:
    result = verify_citations("A [1]. B [1]. C [1].", _contexts(1))
    assert [c.marker for c in result.citations] == [1]


def test_no_markers_no_citations() -> None:
    result = verify_citations("A plain answer with no citations.", _contexts(2))
    assert result.citations == []
    assert result.unsupported_markers == []


def test_grouped_markers_are_expanded() -> None:
    result = verify_citations("Both sources apply [1, 3].", _contexts(3))
    assert result.unsupported_markers == []
    assert [c.marker for c in result.citations] == [1, 3]
    assert "[1][3]" in result.text
    assert "[1, 3]" not in result.text


def test_grouped_markers_drop_dangling_members() -> None:
    result = verify_citations("Mixed group [1,9].", _contexts(2))
    assert result.unsupported_markers == [9]
    assert [c.marker for c in result.citations] == [1]
    assert "[1]" in result.text
    assert "9" not in result.text
