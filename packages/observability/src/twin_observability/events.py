"""Step events — the one observable-progress contract shared by every layer.

A pipeline stage emits a :class:`StepEvent`; *where* that event goes is the caller's
choice, expressed as an :data:`EventSink` (a plain callable). The API wraps a sink
that pushes to an SSE queue; the CLI wraps one that logs; :class:`RunTrace` wraps one
that appends to a JSONL file. Stages therefore stay framework-free and unit-testable
without any live stream.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, Self

from pydantic import BaseModel, Field

from twin_observability.correlation import get_correlation_id
from twin_observability.logging import get_logger

log = get_logger(__name__)

Phase = Literal["start", "progress", "complete"]


class StepEvent(BaseModel):
    """A single observable moment in a pipeline run (ingest or answer)."""

    node: str = Field(description="Name of the emitting stage, e.g. 'retrieve'")
    phase: Phase = "progress"
    message: str = Field(description="Human-readable status line")
    data: dict[str, Any] = Field(default_factory=dict)
    tokens: int | None = Field(default=None, description="LLM tokens used by this step, if any")
    ts: float = Field(default_factory=time.time)


#: Anything that consumes step events. Kept a bare callable so callers compose freely.
EventSink = Callable[[StepEvent], None]


def log_sink(event: StepEvent) -> None:
    """An :data:`EventSink` that writes each event to the structured log."""
    log.info(
        "step",
        node=event.node,
        phase=event.phase,
        message=event.message,
        tokens=event.tokens,
    )


def combine_sinks(*sinks: EventSink | None) -> EventSink:
    """Fan one event out to several sinks; ``None`` entries are skipped."""
    active = [s for s in sinks if s is not None]

    def _emit(event: StepEvent) -> None:
        for sink in active:
            sink(event)

    return _emit


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len] or "run"


class RunTrace:
    """Persist a run to ``<trace_dir>/<timestamp>-<slug>.jsonl`` — grep-able, diff-able, no account.

    Layout: a ``run`` header line, one ``step`` line per event, then a final ``result``
    line. Use as a context manager and pass :attr:`sink` into a pipeline::

        with RunTrace("answer", "what is x", trace_dir=Path("runs")) as trace:
            answer = pipeline.run(question, sink=trace.sink)
            trace.finish({"answer": answer.text})

    When ``enabled`` is False every method is a no-op and no file is created.
    """

    def __init__(
        self,
        kind: str,
        label: str,
        *,
        trace_dir: Path,
        enabled: bool = True,
    ) -> None:
        self.kind = kind
        self.enabled = enabled
        self.path: Path | None = None
        self._fh: Any = None
        if not enabled:
            return
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        trace_dir.mkdir(parents=True, exist_ok=True)
        self.path = trace_dir / f"{stamp}-{_slugify(label)}.jsonl"

    def __enter__(self) -> Self:
        if self.enabled and self.path is not None:
            self._fh = self.path.open("w", encoding="utf-8")
            self._write(
                {
                    "type": "run",
                    "kind": self.kind,
                    "correlation_id": get_correlation_id(),
                    "ts": time.time(),
                }
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def sink(self, event: StepEvent) -> None:
        """An :data:`EventSink` that appends the event as a ``step`` line."""
        self._write({"type": "step", **event.model_dump()})

    def finish(self, result: dict[str, Any]) -> None:
        """Write the terminal ``result`` line."""
        self._write({"type": "result", "ts": time.time(), **result})

    def _write(self, record: dict[str, Any]) -> None:
        if self._fh is None:
            return
        self._fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()
