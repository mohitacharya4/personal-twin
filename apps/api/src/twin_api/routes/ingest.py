"""The ``/ingest`` endpoint — index configured sources on demand.

Runs the (synchronous) ingest pipeline in a worker thread so the event loop stays
responsive, and returns the counts. For large corpora this would move to a background
job; for a personal twin an inline call with a clear response is the right amount.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from twin_observability import get_logger
from twin_rag import IngestPipeline

log = get_logger(__name__)

router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    """Which source to (re)index. Both fields optional: default indexes everything."""

    source: str | None = None
    reset: bool = False


@router.post("/ingest", summary="Index configured sources into the vector store")
async def ingest(request: Request, payload: IngestRequest) -> dict[str, Any]:
    """Trigger ingestion and return what was indexed."""
    pipeline: IngestPipeline = request.app.state.ingest_pipeline
    try:
        report = await asyncio.to_thread(
            pipeline.run, source_id=payload.source, reset=payload.reset
        )
    except ValueError as exc:  # unknown source id, bad config
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("ingest.endpoint_failed")
        raise HTTPException(status_code=500, detail="Ingestion failed.") from exc
    return report.model_dump()
