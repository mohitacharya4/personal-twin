"""Chroma-backed vector store — the local-first default.

Embedded, persists to disk, needs no external service. The collection is configured for
cosine space; Chroma returns cosine *distance*, which we convert to a similarity score
(``1 - distance``) so higher always means more relevant across backends.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from twin_rag.models import Chunk, EmbeddedChunk, ScoredChunk

#: Chunk-metadata keys Chroma stores as its own columns; the chunk text is the document.
_META_KEYS = ("doc_id", "source_id", "title", "ordinal")


class ChromaVectorStore:
    """A :class:`~twin_rag.vectorstore.base.VectorStore` over a persistent Chroma collection."""

    def __init__(self, path: Path, *, collection_name: str = "twin") -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collection_name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, records: list[EmbeddedChunk]) -> None:
        if not records:
            return
        self._collection.upsert(
            ids=[r.chunk.id for r in records],
            # list[list[float]] is fine at runtime; Chroma's signature is invariant.
            embeddings=[r.embedding for r in records],  # type: ignore[arg-type]
            documents=[r.chunk.text for r in records],
            metadatas=[self._to_metadata(r.chunk) for r in records],
        )

    def similarity_search(
        self,
        embedding: list[float],
        *,
        k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        result = self._collection.query(
            query_embeddings=[embedding],  # type: ignore[arg-type]  # invariant Chroma signature
            n_results=k,
            where=dict(where) if where else None,
            include=["documents", "metadatas", "distances"],
        )
        return self._to_scored(result)

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _to_metadata(chunk: Chunk) -> dict[str, Any]:
        meta: dict[str, Any] = {key: getattr(chunk, key) for key in _META_KEYS}
        # Flatten a couple of useful scalars; Chroma metadata must be primitive.
        if "uri" in chunk.metadata:
            meta["uri"] = chunk.metadata["uri"]
        return meta

    @staticmethod
    def _to_scored(result: Mapping[str, Any]) -> list[ScoredChunk]:
        # Chroma nests results per query; we issue one query, so index [0] throughout.
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        scored: list[ScoredChunk] = []
        for cid, text, meta, dist in zip(ids, docs, metas, dists, strict=True):
            meta = meta or {}
            chunk = Chunk(
                id=cid,
                doc_id=str(meta.get("doc_id", "")),
                source_id=str(meta.get("source_id", "")),
                title=str(meta.get("title", "")),
                ordinal=int(meta.get("ordinal", 0)),
                text=text or "",
                metadata={"uri": meta["uri"]} if "uri" in meta else {},
            )
            scored.append(ScoredChunk(chunk=chunk, score=1.0 - float(dist)))
        return scored
