"""Server-sent events for the answer stream — the contract any frontend consumes.

    event: trace    data: {"node": "retrieve", "detail": "Retrieved 5 candidate chunk(s)"}
    event: token    data: {"text": "I care "}
    event: sources  data: {"citations": [...], "contexts": [...]}
    event: done     data: {"answer": "...", "citations": [...]}
    event: error    data: {"message": "..."}

The shape is stable so a chatbot UI can be built against it independently of the backend.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

EventName = Literal["trace", "token", "sources", "done", "error"]


@dataclass(frozen=True)
class SSEEvent:
    """One server-sent event."""

    name: EventName
    data: dict[str, Any]

    def encode(self) -> str:
        """Wire format. ``json.dumps`` guarantees no bare newline that would end the event early."""
        payload = json.dumps(self.data, separators=(",", ":"), default=str)
        return f"event: {self.name}\ndata: {payload}\n\n"


def trace(node: str, detail: str | None = None) -> SSEEvent:
    """A stage-progress event — what a live pipeline trace renders."""
    return SSEEvent("trace", {"node": node, "detail": detail})


def token(text: str) -> SSEEvent:
    """One chunk of the answer text."""
    return SSEEvent("token", {"text": text})


def sources(citations: list[dict[str, Any]], contexts: list[dict[str, Any]]) -> SSEEvent:
    """The evidence behind the answer: verified citations and the retrieved contexts."""
    return SSEEvent("sources", {"citations": citations, "contexts": contexts})


def done(answer: str, citations: list[dict[str, Any]]) -> SSEEvent:
    """Terminal success event carrying the assembled answer."""
    return SSEEvent("done", {"answer": answer, "citations": citations})


def error(message: str) -> SSEEvent:
    """Terminal failure event. Never leaks internals to the client."""
    return SSEEvent("error", {"message": message})


async def encode_stream(events: AsyncIterator[SSEEvent]) -> AsyncIterator[str]:
    """Encode a stream of events for an HTTP streaming response."""
    async for event in events:
        yield event.encode()
