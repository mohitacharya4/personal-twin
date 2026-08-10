"""Local-directory source and the source registry."""

from __future__ import annotations

from pathlib import Path

import pytest
from twin_rag.sources import LocalDirectorySource, load_sources
from twin_rag.sources.registry import SourceConfigError


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    (root / "sub").mkdir(parents=True)
    (root / "a.md").write_text("# A\nAlpha content.", encoding="utf-8")
    (root / "sub" / "b.txt").write_text("Bravo content.", encoding="utf-8")
    (root / "ignore.png").write_bytes(b"\x89PNG")
    return root


def test_list_all_finds_supported_files_only(tmp_path: Path) -> None:
    source = LocalDirectorySource("docs", _corpus(tmp_path))
    refs = list(source.list_all())
    uris = {r.uri for r in refs}
    assert uris == {"a.md", "sub/b.txt"}
    assert all(r.source_id == "docs" for r in refs)


def test_fetch_reads_text(tmp_path: Path) -> None:
    source = LocalDirectorySource("docs", _corpus(tmp_path))
    ref = next(r for r in source.list_all() if r.uri == "a.md")
    doc = source.fetch(ref)
    assert "Alpha content." in doc.text


def test_missing_directory_raises(tmp_path: Path) -> None:
    source = LocalDirectorySource("docs", tmp_path / "nope")
    with pytest.raises(FileNotFoundError):
        list(source.list_all())


def test_source_id_may_not_contain_colon(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="':'"):
        LocalDirectorySource("bad:id", tmp_path)


def test_registry_loads_local_dir(tmp_path: Path) -> None:
    _corpus(tmp_path)
    config = tmp_path / "sources.yaml"
    config.write_text(
        "sources:\n  - id: docs\n    type: local_dir\n    root: corpus\n", encoding="utf-8"
    )
    sources = load_sources(config)
    assert [s.id for s in sources] == ["docs"]
    assert {r.uri for r in sources[0].list_all()} == {"a.md", "sub/b.txt"}


def test_registry_rejects_unknown_type(tmp_path: Path) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text("sources:\n  - id: x\n    type: quantum\n", encoding="utf-8")
    with pytest.raises(SourceConfigError, match="unknown source type"):
        load_sources(config)


def test_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    (tmp_path / "corpus").mkdir()
    config = tmp_path / "sources.yaml"
    config.write_text(
        "sources:\n"
        "  - id: docs\n    type: local_dir\n    root: corpus\n"
        "  - id: docs\n    type: local_dir\n    root: corpus\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceConfigError, match="duplicate"):
        load_sources(config)


def test_registry_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(SourceConfigError, match="not found"):
        load_sources(tmp_path / "absent.yaml")
