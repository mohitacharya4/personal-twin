"""Correlation-id propagation.

One id per request/run, carried through every log line so a single user question is
traceable end to end. Transport-agnostic on purpose: this module knows nothing about
HTTP, so a CLI ingest run or an eval sweep can use it too.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

CORRELATION_ID_HEADER = "X-Correlation-ID"

_correlation_id: ContextVar[str | None] = ContextVar("twin_correlation_id", default=None)


def new_correlation_id() -> str:
    """Generate a fresh correlation id."""
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """The correlation id for the current context, if one is bound."""
    return _correlation_id.get()


def set_correlation_id(value: str) -> Token[str | None]:
    """Bind a correlation id to the current context. Returns a token for resetting."""
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Restore the previous correlation id."""
    _correlation_id.reset(token)


@contextmanager
def correlation_scope(value: str | None = None) -> Iterator[str]:
    """Bind a correlation id for the duration of a block, restoring the previous one after.

    Generates one when not supplied, so a background task always has an id.
    """
    correlation_id = value or new_correlation_id()
    token = set_correlation_id(correlation_id)
    try:
        yield correlation_id
    finally:
        reset_correlation_id(token)
