"""Pluggable vector-store backends behind a single Protocol."""

from __future__ import annotations

from twin_rag.vectorstore.base import VectorStore
from twin_rag.vectorstore.factory import get_vector_store

__all__ = ["VectorStore", "get_vector_store"]
