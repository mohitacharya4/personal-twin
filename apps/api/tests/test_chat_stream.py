"""The /chat endpoint streams trace, token, sources, and done events over SSE."""

from __future__ import annotations

import json
from typing import Any

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from twin_api.assembly import Backend
from twin_api.main import create_app
from twin_config import AppEnv, Settings
from twin_rag import AnswerPipeline, IngestPipeline, Retriever
from twin_rag.testing import HashEmbedder, ListSource, MemoryVectorStore, make_fake_chat_model


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


async def test_out_of_scope_answer_emits_no_sources() -> None:
    # A retriever whose floor nothing can clear -> no context -> honest fallback, no sources.
    store = MemoryVectorStore()
    embedder = HashEmbedder()
    retriever = Retriever(embedder, store, top_k=3, min_score=1.1)
    backend = Backend(
        store=store,
        ingest_pipeline=IngestPipeline(
            [ListSource("docs", {"a.md": "x"})], embedder, store, chunk_size=200, chunk_overlap=0
        ),
        answer_pipeline=AnswerPipeline(retriever, make_fake_chat_model("SHOULD NOT APPEAR [1]")),
    )
    app = create_app(Settings(_env_file=None, app_env=AppEnv.TEST), backend=backend)  # type: ignore[call-arg]
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"question": "What is the capital of France?"})

    events = _parse_sse(resp.text)
    names = [name for name, _ in events]
    assert "sources" not in names
    done_payload = next(data for name, data in events if name == "done")
    assert "don't have information" in done_payload["answer"]
    assert done_payload["citations"] == []
