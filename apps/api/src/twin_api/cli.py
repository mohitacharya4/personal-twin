"""``twin`` command-line entry point.

Subcommands:
    twin serve      Run the API with uvicorn.
    twin ingest     Index configured sources into the vector store (Phase 2).

The CLI is deliberately thin: it parses arguments, configures logging, and delegates
to the same code paths the API uses.
"""

from __future__ import annotations

import argparse
import sys

from twin_config import ConfigError, get_settings
from twin_observability import configure_logging, get_logger

log = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twin", description="Personal Twin — RAG backend CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the API with uvicorn")
    serve.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev)")

    ingest = sub.add_parser("ingest", help="Index configured sources into the vector store")
    ingest.add_argument(
        "--source",
        default=None,
        help="Ingest only the named source id (default: every source in sources.yaml)",
    )
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="Clear the collection before indexing (full rebuild)",
    )
    return parser


def _serve(reload: bool) -> int:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "twin_api.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=reload,
    )
    return 0


def _ingest(source: str | None, reset: bool) -> int:
    # Imported lazily so `twin serve` doesn't pull in the RAG stack.
    from twin_api.ingest_runner import run_ingest

    return run_ingest(source=source, reset=reset)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    settings = None
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    configure_logging(level=settings.log_level, json_output=settings.app_env != "dev")

    if args.command == "serve":
        return _serve(args.reload)
    if args.command == "ingest":
        return _ingest(args.source, args.reset)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
