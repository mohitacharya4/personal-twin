"""Pick a vector-store backend from settings — the one place backends are chosen."""

from __future__ import annotations

from twin_config import Settings, get_settings

from twin_rag.vectorstore.base import VectorStore


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    """Construct the configured vector store (``chroma`` by default, ``pgvector`` opt-in)."""
    settings = settings or get_settings()
    backend = settings.vector_store_backend

    if backend == "chroma":
        from twin_rag.vectorstore.chroma import ChromaVectorStore

        return ChromaVectorStore(settings.chroma_path)

    if backend == "pgvector":
        if not settings.database_url:
            raise ValueError(
                "TWIN_VECTOR_STORE_BACKEND=pgvector requires TWIN_DATABASE_URL. "
                "Set it in .env or switch the backend back to 'chroma'."
            )
        from twin_rag.vectorstore.pgvector import PgVectorStore

        return PgVectorStore(settings.database_url)

    raise ValueError(f"Unknown vector store backend: {backend!r}")
