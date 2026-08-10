"""Operational endpoints — liveness and a readiness view of the backing store."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from starlette.requests import Request
from twin_config import Settings
from twin_observability import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["ops"])


@router.get("/health", summary="Liveness + a readiness view of config and the vector store")
async def health(request: Request) -> dict[str, Any]:
    """Report configuration, tracing, and vector-store reachability.

    Never raises: a degraded dependency is reported as ``ok: false`` with a reason, so
    the endpoint stays a reliable probe rather than a source of 500s.
    """
    settings: Settings = request.app.state.settings
    body: dict[str, Any] = {
        "status": "ok",
        "env": settings.app_env,
        "tracing": settings.tracing_enabled,
        "vector_store": {
            "backend": settings.vector_store_backend,
            "ok": None,
            "documents": None,
        },
    }

    store = getattr(request.app.state, "vector_store", None)
    if store is not None:
        try:
            body["vector_store"]["documents"] = store.count()
            body["vector_store"]["ok"] = True
        except Exception as exc:
            log.warning("health.vector_store_unreachable", error=str(exc))
            body["vector_store"]["ok"] = False
            body["status"] = "degraded"

    return body
