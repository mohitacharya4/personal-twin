"""Structured JSON logging — logs as event streams.

Every line is JSON, carries the correlation id, and is written to stdout for the
platform to collect. Never log secrets or full document contents; the redactor below
is a backstop, not a licence to.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from twin_observability.correlation import get_correlation_id

# Env var / kwarg names whose values must never reach a log line.
_REDACT_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "database_url",
        "anthropic_api_key",
        "openai_api_key",
        "langsmith_api_key",
    }
)
_REDACTED = "***redacted***"


def add_correlation_id(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Attach the current correlation id to every event, when one is bound."""
    correlation_id = get_correlation_id()
    if correlation_id is not None:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def redact_secrets(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Redact obviously-sensitive keys — catches the accidental ``log.info("boot", **settings)``."""
    for key in list(event_dict):
        if key.lower() in _REDACT_KEYS:
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    """Configure structlog + stdlib logging. Idempotent; safe to call at every boot.

    ``json_output=False`` gives a human-readable console renderer for local runs.
    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_correlation_id,
        redact_secrets,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )

    # Route stdlib loggers (uvicorn, httpx, ...) through the same stream.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """A bound logger. Prefer module-level ``log = get_logger(__name__)``."""
    logger = structlog.get_logger()
    return logger.bind(logger=name) if name else logger  # type: ignore[no-any-return]
