"""The Personal Twin RAG pipeline.

Each stage is a small typed unit behind a Protocol so it is swappable and unit-testable
in isolation: sources → chunking → embeddings → vector store → (retrieval → generation).
"""

from __future__ import annotations

from twin_rag.chunking import chunk_document
from twin_rag.citations import CitationResult, verify_citations
from twin_rag.embeddings import get_embedder
from twin_rag.generation import generate_answer
from twin_rag.llm import get_llm
from twin_rag.models import (
    Answer,
    Chunk,
    Citation,
    EmbeddedChunk,
    RawDocument,
    ScoredChunk,
    SourceRef,
    make_chunk_id,
)
from twin_rag.pipeline import AnswerPipeline, IngestPipeline, IngestReport
from twin_rag.registry import ModelRegistry
from twin_rag.retriever import NoOpReranker, Reranker, Retriever
from twin_rag.sources import DocumentSource, LocalDirectorySource, load_sources
from twin_rag.vectorstore import VectorStore, get_vector_store

__all__ = [
    "Answer",
    "AnswerPipeline",
    "Chunk",
    "Citation",
    "CitationResult",
    "DocumentSource",
    "EmbeddedChunk",
    "IngestPipeline",
    "IngestReport",
    "LocalDirectorySource",
    "ModelRegistry",
    "NoOpReranker",
    "RawDocument",
    "Reranker",
    "Retriever",
    "ScoredChunk",
    "SourceRef",
    "VectorStore",
    "chunk_document",
    "generate_answer",
    "get_embedder",
    "get_llm",
    "get_vector_store",
    "load_sources",
    "make_chunk_id",
    "verify_citations",
]
