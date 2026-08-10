"""Assemble and run the ingest pipeline for the ``twin ingest`` CLI.

Thin glue: build the configured sources, embedder, and vector store, run the pipeline
inside a correlation scope + JSONL trace, and print a human summary. The API reuses the
same builders (:mod:`twin_api.assembly`) so CLI and server index identically.
"""

from __future__ import annotations

from twin_config import get_settings
from twin_observability import RunTrace, combine_sinks, correlation_scope, get_logger, log_sink

from twin_api.assembly import build_ingest_pipeline

log = get_logger(__name__)


def run_ingest(*, source: str | None = None, reset: bool = False) -> int:
    """Run ingestion and return a process exit code (0 on success, 1 on failure)."""
    settings = get_settings()
    pipeline = build_ingest_pipeline(settings)

    label = source or "all-sources"
    with (
        correlation_scope(),
        RunTrace(
            "ingest", label, trace_dir=settings.trace_dir, enabled=settings.persist_traces
        ) as trace,
    ):
        try:
            report = pipeline.run(
                source_id=source,
                reset=reset,
                sink=combine_sinks(log_sink, trace.sink),
            )
        except Exception as exc:
            log.exception("ingest.failed")
            print(f"Ingest failed: {exc}")  # noqa: T201
            return 1
        trace.finish(report.model_dump())

    print(  # noqa: T201
        f"Indexed {report.chunks} chunks from {report.documents} documents "
        f"across {len(report.per_source)} source(s)."
    )
    for source_id, count in report.per_source.items():
        print(f"  - {source_id}: {count} chunks")  # noqa: T201
    if trace.path is not None:
        print(f"Trace: {trace.path}")  # noqa: T201
    return 0
