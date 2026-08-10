"""The ``DocumentSource`` port.

Adding a source (Confluence, Notion, S3, a database) means implementing this protocol
and registering it — chunking, embedding, indexing, retrieval, and generation stay
untouched. Implementations live in their own module and are the *only* place a source
SDK (``boto3``, a Confluence client, …) may be imported.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from twin_rag.models import RawDocument, SourceRef


@runtime_checkable
class DocumentSource(Protocol):
    """One pluggable document source. Nothing downstream may branch on which source it is."""

    @property
    def id(self) -> str:
        """Stable namespace for this source, e.g. ``"personal-docs"``. Must contain no ``':'``."""
        ...

    def list_all(self) -> Iterable[SourceRef]:
        """Enumerate every document currently in the source."""
        ...

    def fetch(self, ref: SourceRef) -> RawDocument:
        """Retrieve one document's plain-text content and native metadata."""
        ...
