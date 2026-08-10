"""A document source backed by a local directory.

Reads ``.md``, ``.txt``, and ``.pdf`` files recursively. This is the v1 source that
turns "a folder of your notes" into an answerable corpus; adding a remote source later
is a sibling module implementing the same :class:`~twin_rag.sources.base.DocumentSource`.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from twin_rag.models import RawDocument, SourceRef

#: Extensions we know how to read. Everything else in the tree is ignored.
_TEXT_SUFFIXES = frozenset({".md", ".txt", ".markdown"})
_PDF_SUFFIXES = frozenset({".pdf"})
SUPPORTED_SUFFIXES = _TEXT_SUFFIXES | _PDF_SUFFIXES


class LocalDirectorySource:
    """Index supported files under ``root`` (recursively)."""

    def __init__(self, source_id: str, root: Path) -> None:
        if ":" in source_id:
            msg = f"source id must not contain ':' (got {source_id!r})"
            raise ValueError(msg)
        self._id = source_id
        self._root = root

    @property
    def id(self) -> str:
        return self._id

    def list_all(self) -> Iterable[SourceRef]:
        if not self._root.exists():
            msg = f"source '{self._id}': directory does not exist: {self._root}"
            raise FileNotFoundError(msg)
        for path in sorted(self._root.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                rel = path.relative_to(self._root).as_posix()
                yield SourceRef(
                    source_id=self._id,
                    uri=rel,
                    title=path.stem,
                    metadata={"suffix": path.suffix.lower()},
                )

    def fetch(self, ref: SourceRef) -> RawDocument:
        path = self._root / ref.uri
        suffix = path.suffix.lower()
        if suffix in _PDF_SUFFIXES:
            text = _read_pdf(path)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
        return RawDocument(ref=ref, text=text, metadata={"path": str(path)})


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF, page by page. Empty pages contribute nothing."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())
