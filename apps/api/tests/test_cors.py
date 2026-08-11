"""CORS is enabled for the configured origins so a browser frontend can call the API."""

from __future__ import annotations

from httpx import AsyncClient


async def test_preflight_allows_configured_origin(client: AsyncClient) -> None:
    resp = await client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_actual_request_echoes_allow_origin(client: AsyncClient) -> None:
    resp = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_unlisted_origin_is_not_allowed(client: AsyncClient) -> None:
    resp = await client.get("/health", headers={"Origin": "http://evil.example.com"})
    # Starlette omits the allow-origin header for origins that aren't permitted.
    assert "access-control-allow-origin" not in resp.headers
