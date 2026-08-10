"""Split a document into overlapping, retrievable chunks.

Uses LangChain's recursive splitter, which prefers to break on paragraph → line →
sentence → word boundaries before resorting to a hard cut, so chunks stay semantically
coherent. Each chunk keeps its document's provenance and a deterministic id.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from twin_rag.models import Chunk, RawDocument, make_chunk_id


def chunk_document(doc: RawDocument, *, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Split one document into chunks. Returns ``[]`` for empty/whitespace-only text.

    Args:
        doc: The fetched document.
        chunk_size: Target maximum characters per chunk.
        chunk_overlap: Characters shared between consecutive chunks (keeps context across cuts).
    """
    if not doc.text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        # Coarse → fine: never cut mid-word if a paragraph/line boundary is available.
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    pieces = splitter.split_text(doc.text)
    chunks: list[Chunk] = []
    for ordinal, text in enumerate(pieces):
        cleaned = text.strip()
        if not cleaned:
            continue
        chunks.append(
            Chunk(
                id=make_chunk_id(doc.ref.doc_id, ordinal, cleaned),
                doc_id=doc.ref.doc_id,
                source_id=doc.ref.source_id,
                title=doc.ref.title,
                ordinal=ordinal,
                text=cleaned,
                metadata={**doc.metadata, "uri": doc.ref.uri},
            )
        )
    return chunks
