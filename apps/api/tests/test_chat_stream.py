"""The /chat endpoint streams trace, token, sources, and done events over SSE."""

from __future__ import annotations

import json
from typing import Any

from httpx import AsyncClient


def _parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.strip().split("\n\n"):
        name = data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:") :].strip())
        if name is not None:
            events.append((name, data or {}))
    return events


async def test_chat_streams_grounded_cited_answer(client: AsyncClient) -> None:
    resp = await client.post("/chat", json={"question": "What do you value?"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    names = [name for name, _ in events]

    assert "token" in names
    assert names.count("done") == 1
    assert names[-1] == "done"

    # Stage trace events are emitted before the answer.
    trace_nodes = {data.get("node") for name, data in events if name == "trace"}
    assert {"retrieve", "generate", "verify", "answer"} <= trace_nodes

    done_payload = next(data for name, data in events if name == "done")
    assert "[1]" in done_payload["answer"]
    assert done_payload["citations"][0]["title"] == "Values"

    sources_payload = next(data for name, data in events if name == "sources")
    assert sources_payload["contexts"][0]["title"] == "Values"


async def test_chat_rejects_empty_question(client: AsyncClient) -> None:
    resp = await client.post("/chat", json={"question": ""})
    assert resp.status_code == 422


async def test_chat_accepts_reserved_thread_id(client: AsyncClient) -> None:
    # thread_id is accepted (reserved) even though v1 ignores it.
    resp = await client.post("/chat", json={"question": "What do you value?", "thread_id": "t-1"})
    assert resp.status_code == 200
