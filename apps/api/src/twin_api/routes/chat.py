"""The ``/chat`` endpoint — streams a grounded answer as SSE.

The pipeline is synchronous (a blocking model call), so it runs in a worker thread while
its step events are forwarded to the event loop over a thread-safe queue and emitted as
``trace`` events live. Once the answer is ready it is streamed token-by-token, followed
by its ``sources`` and a terminal ``done``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.requests import Request
from twin_observability import StepEvent, get_logger
from twin_rag import Answer, AnswerPipeline

from twin_api.streaming import SSEEvent, done, encode_stream, error, sources, token, trace

log = get_logger(__name__)

router = APIRouter(tags=["chat"])

#: Pacing for the answer token stream (seconds between chunks). Purely cosmetic.
_TOKEN_DELAY_SECONDS = 0.01

_SENTINEL = object()


class ChatRequest(BaseModel):
    """A question. ``thread_id`` is reserved for multi-turn memory (ignored in v1)."""

    question: Annotated[str, Field(min_length=1, max_length=4000)]
    thread_id: str | None = None


@router.post("/chat", summary="Ask a question; stream a cited answer as SSE")
async def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
    """Stream the answer. Returns immediately; the body arrives incrementally."""
    return StreamingResponse(
        encode_stream(_run(request, payload)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # don't let a proxy defeat streaming
        },
    )


async def _run(request: Request, payload: ChatRequest) -> AsyncIterator[SSEEvent]:
    """Drive the pipeline in a thread, translating its progress into SSE events."""
    pipeline: AnswerPipeline = request.app.state.answer_pipeline
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    holder: dict[str, Any] = {}

    def sink(event: StepEvent) -> None:
        # Called from the worker thread; hop back to the loop thread safely.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def work() -> None:
        try:
            holder["answer"] = pipeline.run(payload.question, sink=sink)
        except Exception as exc:
            holder["error"] = exc
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    loop.run_in_executor(None, work)

    try:
        # Forward stage events live until the pipeline signals completion.
        while True:
            event = await queue.get()
            if event is _SENTINEL:
                break
            yield trace(event.node, event.message)

        if "error" in holder:
            log.error("chat.failed", error=str(holder["error"]))
            yield error("The answer failed. See server logs for the correlation id.")
            return

        answer: Answer = holder["answer"]
        async for evt in _stream_answer(request, answer):
            yield evt

    except asyncio.CancelledError:
        raise


async def _stream_answer(request: Request, answer: Answer) -> AsyncIterator[SSEEvent]:
    """Emit the answer text token-by-token, then its sources and a terminal done."""
    for chunk in _tokenize(answer.text):
        if await request.is_disconnected():
            log.info("chat.client_disconnected")
            return
        yield token(chunk)
        await asyncio.sleep(_TOKEN_DELAY_SECONDS)

    citations = [c.model_dump() for c in answer.citations]
    # Only surface sources when there is grounding context — an out-of-scope answer
    # (nothing cleared the relevance floor) has none, so we don't show empty "sources".
    if answer.contexts:
        contexts = [
            {
                "marker": i,
                "title": s.chunk.title,
                "score": round(s.score, 4),
                "uri": s.chunk.metadata.get("uri"),
            }
            for i, s in enumerate(answer.contexts, start=1)
        ]
        yield sources(citations, contexts)
    yield done(answer.text, citations)


def _tokenize(text: str) -> list[str]:
    """Split into whitespace-preserving chunks so the UI can append without re-joining."""
    return [f"{word} " for word in text.split()] if text else []
