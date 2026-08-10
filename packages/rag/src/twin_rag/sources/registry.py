"""Build configured document sources from ``sources.yaml``.

The registry maps a declared ``type`` to a builder. Code references sources by their
configured ``id``; switching what the twin knows about is an edit to ``sources.yaml``,
never a code change. Adding a new source type = one new builder entry here.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from twin_rag.sources.base import DocumentSource
from twin_rag.sources.local_dir import LocalDirectorySource


class SourceConfigError(ValueError):
    """Raised when ``sources.yaml`` is malformed or names an unknown source type."""


def _build_local_dir(spec: dict[str, Any], *, base_dir: Path) -> DocumentSource:
    try:
        source_id = str(spec["id"])
        root = Path(spec["root"])
    except KeyError as exc:
        msg = f"local_dir source is missing required key {exc}"
        raise SourceConfigError(msg) from exc
    resolved = root if root.is_absolute() else (base_dir / root)
    return LocalDirectorySource(source_id, resolved)


#: type name -> builder. Extend this to add a source type (Confluence, S3, …).
_BUILDERS: dict[str, Callable[..., DocumentSource]] = {
    "local_dir": _build_local_dir,
}


def load_sources(config_path: Path, *, base_dir: Path | None = None) -> list[DocumentSource]:
    """Parse ``sources.yaml`` and build every declared source.

    Args:
        config_path: Path to ``sources.yaml``.
        base_dir: Directory that relative source paths resolve against
            (defaults to the config file's own directory).
    """
    if not config_path.exists():
        msg = f"sources config not found: {config_path}"
        raise SourceConfigError(msg)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    entries = raw.get("sources")
    if not isinstance(entries, list) or not entries:
        msg = f"{config_path} must define a non-empty 'sources' list"
        raise SourceConfigError(msg)

    resolve_base = base_dir or config_path.resolve().parent
    sources: list[DocumentSource] = []
    seen: set[str] = set()
    for spec in entries:
        if not isinstance(spec, dict) or "type" not in spec:
            msg = f"each source needs a 'type'; got: {spec!r}"
            raise SourceConfigError(msg)
        source_type = str(spec["type"])
        builder = _BUILDERS.get(source_type)
        if builder is None:
            known = ", ".join(sorted(_BUILDERS))
            msg = f"unknown source type {source_type!r} (known: {known})"
            raise SourceConfigError(msg)
        source = builder(spec, base_dir=resolve_base)
        if source.id in seen:
            msg = f"duplicate source id {source.id!r}"
            raise SourceConfigError(msg)
        seen.add(source.id)
        sources.append(source)
    return sources
