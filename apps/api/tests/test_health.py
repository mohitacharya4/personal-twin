"""The /health probe reports config, tracing, and store reachability, and never 500s."""

from __future__ import annotations

from httpx import AsyncClient
from twin_observability import CORRELATION_ID_HEADER


async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["env"] == "test"
    assert body["tracing"] is False
    assert body["vector_store"]["backend"] == "chroma"
    # The injected backend has a reachable store seeded with one chunk.
    assert body["vector_store"]["ok"] is True
    assert body["vector_store"]["documents"] == 1


async def test_health_echoes_correlation_id(client: AsyncClient) -> None:
    resp = await client.get("/health", headers={CORRELATION_ID_HEADER: "trace-42"})
    assert resp.headers[CORRELATION_ID_HEADER] == "trace-42"
