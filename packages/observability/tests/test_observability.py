"""Correlation ids, step events, JSONL traces, and the LangSmith bridge."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from twin_config import Settings
from twin_observability import (
    RunTrace,
    StepEvent,
    combine_sinks,
    configure_langsmith,
    correlation_scope,
    get_correlation_id,
)


def test_correlation_scope_binds_and_restores() -> None:
    assert get_correlation_id() is None
    with correlation_scope("abc-123") as cid:
        assert cid == "abc-123"
        assert get_correlation_id() == "abc-123"
    assert get_correlation_id() is None


def test_combine_sinks_fans_out_and_skips_none() -> None:
    seen_a: list[str] = []
    seen_b: list[str] = []
    sink = combine_sinks(lambda e: seen_a.append(e.node), None, lambda e: seen_b.append(e.node))
    sink(StepEvent(node="retrieve", message="hi"))
    assert seen_a == ["retrieve"] == seen_b


def test_run_trace_writes_header_steps_and_result(tmp_path: Path) -> None:
    with RunTrace("answer", "What is X?", trace_dir=tmp_path) as trace:
        assert trace.path is not None
        trace.sink(StepEvent(node="retrieve", phase="complete", message="found 3", tokens=12))
        trace.finish({"answer": "because Y"})

    lines = [json.loads(line) for line in trace.path.read_text(encoding="utf-8").splitlines()]
    assert [rec["type"] for rec in lines] == ["run", "step", "result"]
    assert lines[0]["kind"] == "answer"
    assert lines[1]["node"] == "retrieve"
    assert lines[2]["answer"] == "because Y"


def test_run_trace_disabled_creates_no_file(tmp_path: Path) -> None:
    with RunTrace("answer", "q", trace_dir=tmp_path, enabled=False) as trace:
        trace.sink(StepEvent(node="x", message="y"))
        trace.finish({"answer": "z"})
    assert trace.path is None
    assert list(tmp_path.iterdir()) == []


def test_langsmith_bridge_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    settings = Settings(_env_file=None, langsmith_tracing=False)  # type: ignore[call-arg]
    assert configure_langsmith(settings) is False
    assert os.environ.get("LANGSMITH_TRACING") is None


def test_langsmith_bridge_activates_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_API_KEY", "LANGSMITH_PROJECT"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        langsmith_tracing=True,
        langsmith_api_key="ls-secret",
        langsmith_project="twin-test",
    )
    assert configure_langsmith(settings) is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "twin-test"
