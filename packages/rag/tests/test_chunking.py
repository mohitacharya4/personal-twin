"""Chunking: provenance, determinism, and boundaries."""

from __future__ import annotations

from twin_rag.chunking import chunk_document
from twin_rag.models import RawDocument, SourceRef


def _doc(text: str) -> RawDocument:
    ref = SourceRef(source_id="s", uri="doc.md", title="doc")
    return RawDocument(ref=ref, text=text)


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_document(_doc("   \n\t "), chunk_size=100, chunk_overlap=10) == []


def test_chunks_carry_provenance_and_order() -> None:
    text = "\n\n".join(f"Paragraph number {i} with some words." for i in range(20))
    chunks = chunk_document(_doc(text), chunk_size=120, chunk_overlap=20)

    assert len(chunks) > 1
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.source_id == "s" for c in chunks)
    assert all(c.doc_id == chunks[0].doc_id for c in chunks)
    assert all(c.metadata["uri"] == "doc.md" for c in chunks)


def test_ids_are_deterministic_across_runs() -> None:
    text = "\n\n".join(f"Section {i}." for i in range(10))
    first = chunk_document(_doc(text), chunk_size=100, chunk_overlap=10)
    second = chunk_document(_doc(text), chunk_size=100, chunk_overlap=10)
    assert [c.id for c in first] == [c.id for c in second]


def test_edit_changes_only_affected_ids() -> None:
    base = "\n\n".join(f"Section {i}." for i in range(10))
    edited = base.replace("Section 9.", "Section nine, edited.")
    a = chunk_document(_doc(base), chunk_size=40, chunk_overlap=0)
    b = chunk_document(_doc(edited), chunk_size=40, chunk_overlap=0)
    # The early chunks are untouched, so their content-addressed ids match.
    assert a[0].id == b[0].id
