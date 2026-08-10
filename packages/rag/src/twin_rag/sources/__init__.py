"""Pluggable document sources."""

from __future__ import annotations

from twin_rag.sources.base import DocumentSource
from twin_rag.sources.local_dir import LocalDirectorySource
from twin_rag.sources.registry import SourceConfigError, load_sources

__all__ = [
    "DocumentSource",
    "LocalDirectorySource",
    "SourceConfigError",
    "load_sources",
]
