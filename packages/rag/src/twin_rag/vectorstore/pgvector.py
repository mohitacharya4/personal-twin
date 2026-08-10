"""pgvector-backed vector store — the opt-in production backend.

Same :class:`~twin_rag.vectorstore.base.VectorStore` contract as Chroma, over Postgres +
the ``pgvector`` extension. Enabled with ``TWIN_VECTOR_STORE_BACKEND=pgvector`` and the
``pgvector`` extra (``uv sync --extra pgvector``). The embedding column's dimension is
fixed on first upsert to match the embedder — switching embedders means a fresh table.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from twin_rag.models import Chunk, EmbeddedChunk, ScoredChunk


class PgVectorStore:
    """A vector store over a single ``chunks`` table in Postgres."""

    def __init__(self, dsn: str, *, table: str = "twin_chunks") -> None:
        try:
            import psycopg
            from pgvector.psycopg import register_vector
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "The 'pgvector' extra is not installed. Run: uv sync --extra pgvector"
            ) from exc

        self._table = _validate_identifier(table)
        self._conn = psycopg.connect(dsn, autocommit=True)
        self._conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self._conn)
        self._dim: int | None = None
        self._ensure_dim_from_existing()

    def upsert(self, records: list[EmbeddedChunk]) -> None:
        if not records:
            return
        self._ensure_table(len(records[0].embedding))
        with self._conn.cursor() as cur:
            cur.executemany(
                f"""
                INSERT INTO {self._table}
                    (id, doc_id, source_id, title, ordinal, text, uri, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    doc_id = EXCLUDED.doc_id, source_id = EXCLUDED.source_id,
                    title = EXCLUDED.title, ordinal = EXCLUDED.ordinal,
                    text = EXCLUDED.text, uri = EXCLUDED.uri, embedding = EXCLUDED.embedding
                """,
                [self._row(r) for r in records],
            )

    def similarity_search(
        self,
        embedding: list[float],
        *,
        k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        if self._dim is None:  # nothing indexed yet
            return []
        clause, params = _where_clause(where)
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, doc_id, source_id, title, ordinal, text, uri,
                       1 - (embedding <=> %s::vector) AS score
                FROM {self._table}
                {clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [_vec(embedding), *params, _vec(embedding), k],
            )
            rows = cur.fetchall()
        return [self._scored(row) for row in rows]

    def count(self) -> int:
        if self._dim is None:
            return 0
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def reset(self) -> None:
        self._conn.execute(f"DROP TABLE IF EXISTS {self._table}")
        self._dim = None

    # -- internals --------------------------------------------------------
    def _ensure_dim_from_existing(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", [self._table])
            row = cur.fetchone()
        if row and row[0] is not None:
            with self._conn.cursor() as cur:
                cur.execute(f"SELECT vector_dims(embedding) FROM {self._table} LIMIT 1")
                dim_row = cur.fetchone()
            if dim_row:
                self._dim = int(dim_row[0])

    def _ensure_table(self, dim: int) -> None:
        if self._dim == dim:
            return
        if self._dim is not None and self._dim != dim:
            msg = (
                f"embedding dimension changed ({self._dim} -> {dim}); this is a migration. "
                f"Drop/rebuild the '{self._table}' table with the new embedder."
            )
            raise ValueError(msg)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                ordinal INT NOT NULL,
                text TEXT NOT NULL,
                uri TEXT,
                embedding vector({dim}) NOT NULL
            )
            """
        )
        self._dim = dim

    @staticmethod
    def _row(record: EmbeddedChunk) -> tuple[Any, ...]:
        c = record.chunk
        return (
            c.id,
            c.doc_id,
            c.source_id,
            c.title,
            c.ordinal,
            c.text,
            c.metadata.get("uri"),
            _vec(record.embedding),
        )

    @staticmethod
    def _scored(row: tuple[Any, ...]) -> ScoredChunk:
        cid, doc_id, source_id, title, ordinal, text, uri, score = row
        return ScoredChunk(
            chunk=Chunk(
                id=cid,
                doc_id=doc_id,
                source_id=source_id,
                title=title,
                ordinal=ordinal,
                text=text,
                metadata={"uri": uri} if uri else {},
            ),
            score=float(score),
        )


def _vec(embedding: list[float]) -> str:
    """pgvector's text input format: ``[1,2,3]``."""
    return json.dumps(embedding)


def _where_clause(where: Mapping[str, Any] | None) -> tuple[str, list[Any]]:
    """Build a safe ``WHERE`` from equality filters on the known metadata columns."""
    if not where:
        return "", []
    allowed = {"doc_id", "source_id", "title", "ordinal"}
    parts: list[str] = []
    params: list[Any] = []
    for key, value in where.items():
        if key not in allowed:
            msg = f"unsupported filter column {key!r} (allowed: {sorted(allowed)})"
            raise ValueError(msg)
        parts.append(f"{key} = %s")
        params.append(value)
    return "WHERE " + " AND ".join(parts), params


def _validate_identifier(name: str) -> str:
    """Guard the table name — it is interpolated into SQL, so it must be an identifier."""
    if not name.replace("_", "").isalnum():
        msg = f"invalid table identifier: {name!r}"
        raise ValueError(msg)
    return name
