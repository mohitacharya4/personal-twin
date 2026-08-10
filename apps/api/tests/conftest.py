"""Shared fixtures: an app + client wired to a real pipeline over offline fakes.

The backend is built from :mod:`twin_rag.testing` doubles (hash embedder, in-memory
store, canned chat model), so the API tests exercise the *real* routes, SSE runner, and
pipeline end to end without a live model or network.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from twin_api.assembly import Backend
from twin_api.main import create_app
from twin_config import AppEnv, Settings
from twin_rag import AnswerPipeline, IngestPipeline, Retriever
from twin_rag.models import Chunk, EmbeddedChunk
from twin_rag.testing import HashEmbedder, ListSource, MemoryVectorStore, make_fake_chat_model

CANNED_ANSWER = "I value tests and observability [1]."


def build_test_backend() -> Backend:
    """A backend seeded with one document and a canned, citing answer."""
    store = MemoryVectorStore()
    embedder = HashEmbedder()
    seed = Chunk(
        id="c1",
        doc_id="d",
        source_id="personal",
        title="Values",
        ordinal=0,
        text="I value tests and observability.",
        metadata={"uri": "values.md"},
    )
    store.upsert([EmbeddedChunk(chunk=seed, embedding=embedder.embed_query(seed.text))])

    retriever = Retriever(embedder, store, top_k=3)
    answer_pipeline = AnswerPipeline(retriever, make_fake_chat_model(CANNED_ANSWER))
    ingest_pipeline = IngestPipeline(
        [ListSource("docs", {"a.md": "Doc A about testing.", "b.md": "Doc B about tracing."})],
        embedder,
        store,
        chunk_size=200,
        chunk_overlap=0,
    )
    return Backend(store=store, ingest_pipeline=ingest_pipeline, answer_pipeline=answer_pipeline)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, app_env=AppEnv.TEST)  # type: ignore[call-arg]


@pytest.fixture
def backend() -> Backend:
    return build_test_backend()


@pytest_asyncio.fixture
async def client(settings: Settings, backend: Backend) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, backend=backend)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
