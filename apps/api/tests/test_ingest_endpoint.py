"""The /ingest endpoint indexes configured sources and reports counts."""

from __future__ import annotations

from httpx import AsyncClient


async def test_ingest_indexes_and_reports(client: AsyncClient) -> None:
    resp = await client.post("/ingest", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["documents"] == 2
    assert body["chunks"] >= 2
    assert body["per_source"]["docs"] == body["chunks"]


async def test_ingest_unknown_source_is_400(client: AsyncClient) -> None:
    resp = await client.post("/ingest", json={"source": "ghost"})
    assert resp.status_code == 400
    assert "ghost" in resp.json()["detail"]
