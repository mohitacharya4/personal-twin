"""End-to-end pipelines wiring the stages together.

:class:`IngestPipeline` turns configured sources into an indexed corpus
(source → fetch → chunk → embed → upsert). The answer path (:class:`AnswerPipeline`)
lands in Phase 3. Both emit :class:`~twin_observability.StepEvent`s through an optional
sink so a run is observable live (SSE), on the CLI, and in a JSONL trace.
"""

from __future__ import annotations

from collections.abc import Iterable

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from twin_observability import EventSink, StepEvent, get_logger

from twin_rag.chunking import chunk_document
from twin_rag.citations import verify_citations
from twin_rag.generation import generate_answer
from twin_rag.models import Answer, Chunk, EmbeddedChunk
from twin_rag.retriever import Retriever
from twin_rag.sources.base import DocumentSource
from twin_rag.vectorstore.base import VectorStore

log = get_logger(__name__)


class IngestReport(BaseModel):
    """What one ingest run indexed."""

    documents: int = 0
    chunks: int = 0
    per_source: dict[str, int] = Field(default_factory=dict)


def _emit(sink: EventSink | None, event: StepEvent) -> None:
    if sink is not None:
        sink(event)


class IngestPipeline:
    """Index configured sources into the vector store. Idempotent: re-runs upsert by id."""

    def __init__(
        self,
        sources: Iterable[DocumentSource],
        embedder: Embeddings,
        store: VectorStore,
        *,
        chunk_size: int,
        chunk_overlap: int,
        embed_batch_size: int = 64,
    ) -> None:
        self._sources = list(sources)
        self._embedder = embedder
        self._store = store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embed_batch_size = embed_batch_size

    def run(
        self,
        *,
        source_id: str | None = None,
        reset: bool = False,
        sink: EventSink | None = None,
    ) -> IngestReport:
        """Ingest every configured source (or just ``source_id``).

        Args:
            source_id: Restrict to one source id; ``None`` ingests all.
            reset: Clear the collection before indexing (full rebuild).
            sink: Optional step-event sink for live progress.
        """
        selected = self._select(source_id)
        if reset:
            _emit(sink, StepEvent(node="ingest", phase="start", message="Resetting collection"))
            self._store.reset()

        report = IngestReport()
        for source in selected:
            indexed = self._ingest_source(source, sink)
            report.per_source[source.id] = indexed.chunks
            report.documents += indexed.documents
            report.chunks += indexed.chunks

        _emit(
            sink,
            StepEvent(
                node="ingest",
                phase="complete",
                message=f"Indexed {report.chunks} chunks from {report.documents} documents",
                data=report.model_dump(),
            ),
        )
        log.info("ingest.complete", documents=report.documents, chunks=report.chunks)
        return report

    def _select(self, source_id: str | None) -> list[DocumentSource]:
        if source_id is None:
            return self._sources
        matches = [s for s in self._sources if s.id == source_id]
        if not matches:
            known = ", ".join(s.id for s in self._sources) or "(none)"
            msg = f"no configured source with id {source_id!r} (known: {known})"
            raise ValueError(msg)
        return matches

    def _ingest_source(self, source: DocumentSource, sink: EventSink | None) -> IngestReport:
        _emit(sink, StepEvent(node="ingest", message=f"Reading source '{source.id}'"))
        docs = 0
        chunks: list[Chunk] = []
        for ref in source.list_all():
            raw = source.fetch(ref)
            doc_chunks = chunk_document(
                raw, chunk_size=self._chunk_size, chunk_overlap=self._chunk_overlap
            )
            if doc_chunks:
                docs += 1
                chunks.extend(doc_chunks)

        self._embed_and_store(chunks, sink)
        return IngestReport(documents=docs, chunks=len(chunks), per_source={source.id: len(chunks)})

    def _embed_and_store(self, chunks: list[Chunk], sink: EventSink | None) -> None:
        for start in range(0, len(chunks), self._embed_batch_size):
            batch = chunks[start : start + self._embed_batch_size]
            vectors = self._embedder.embed_documents([c.text for c in batch])
            self._store.upsert(
                [EmbeddedChunk(chunk=c, embedding=v) for c, v in zip(batch, vectors, strict=True)]
            )
            _emit(
                sink,
                StepEvent(
                    node="embed",
                    message=f"Embedded {min(start + len(batch), len(chunks))}/{len(chunks)} chunks",
                ),
            )


class AnswerPipeline:
    """Answer a question: retrieve → generate → verify citations → :class:`Answer`.

    Stateless in v1 (no conversation memory). Emits a step event per stage so the run is
    observable live over SSE, on the CLI, and in a JSONL trace.
    """

    def __init__(self, retriever: Retriever, generator: BaseChatModel) -> None:
        self._retriever = retriever
        self._generator = generator

    def run(self, question: str, *, sink: EventSink | None = None) -> Answer:
        """Produce a grounded, citation-verified answer to ``question``."""
        _emit(sink, StepEvent(node="answer", phase="start", message="Answering question"))

        contexts = self._retriever.retrieve(question, sink=sink)
        if not contexts:
            _emit(
                sink,
                StepEvent(node="answer", phase="complete", message="No relevant context found"),
            )
            return Answer(
                text="I don't have information about that in my knowledge base.",
                contexts=[],
            )

        _emit(sink, StepEvent(node="generate", message="Generating grounded answer"))
        raw_text, usage = generate_answer(self._generator, question, contexts)

        verified = verify_citations(raw_text, contexts)
        if verified.unsupported_markers:
            log.warning("answer.unsupported_citations", markers=verified.unsupported_markers)
        _emit(
            sink,
            StepEvent(
                node="verify",
                phase="complete",
                message=f"Verified {len(verified.citations)} citation(s)",
                tokens=usage.get("total_tokens"),
                data={"unsupported": verified.unsupported_markers},
            ),
        )

        answer = Answer(
            text=verified.text,
            citations=verified.citations,
            contexts=contexts,
            unsupported_markers=verified.unsupported_markers,
            usage=usage,
        )
        _emit(sink, StepEvent(node="answer", phase="complete", message="Answer ready"))
        return answer
