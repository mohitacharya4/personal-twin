"""FastAPI application factory.

Boot order matters: configuration is validated **before** anything else starts, so a
misconfigured process dies immediately with a clear message instead of failing at the
first request. Heavy resources (the vector store, the RAG pipelines) are built once in
the lifespan and stashed on ``app.state`` for handlers to reuse.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twin_config import Settings, get_settings
from twin_observability import configure_langsmith, configure_logging, get_logger

from twin_api.assembly import Backend, build_backend
from twin_api.health import router as ops_router
from twin_api.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from twin_api.routes.chat import router as chat_router
from twin_api.routes.ingest import router as ingest_router

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Acquire resources on start; release them on shutdown."""
    settings: Settings = app.state.settings

    backend: Backend = getattr(app.state, "backend", None) or build_backend(settings)
    app.state.backend = backend
    app.state.vector_store = backend.store
    app.state.ingest_pipeline = backend.ingest_pipeline
    app.state.answer_pipeline = backend.answer_pipeline

    log.info("api.started", env=settings.app_env, tracing=settings.tracing_enabled)
    try:
        yield
    finally:
        log.info("api.stopped")


def create_app(settings: Settings | None = None, *, backend: Backend | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: Injected settings (so tests need no environment).
        backend: Pre-built pipelines to inject (tests pass fakes; the lifespan builds real
            ones from config when omitted).
    """
    resolved = settings or get_settings()

    configure_logging(level=resolved.log_level, json_output=resolved.app_env != "dev")
    configure_langsmith(resolved)

    app = FastAPI(
        title="Personal Twin",
        version="0.1.0",
        summary="Generic, provider-agnostic RAG backend — ask questions, get cited answers.",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    if backend is not None:
        app.state.backend = backend

    # Order matters (middleware runs bottom-up on the request): correlation ids are bound
    # outermost so every log line — including the request-logging middleware's own — carries
    # one, and CORS runs first on the response so even error responses are browser-readable.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    app.include_router(ops_router)
    app.include_router(chat_router)
    app.include_router(ingest_router)

    return app
