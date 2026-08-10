# Personal Twin

[![CI](https://github.com/mohitacharya4/personal-twin/actions/workflows/ci.yml/badge.svg)](https://github.com/mohitacharya4/personal-twin/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

> A generic, provider-agnostic **RAG backend**. Point it at a folder of documents and it
> answers questions about them over a clean HTTP/SSE API — with **verified citations**,
> switchable LLMs (local [Ollama](https://ollama.com) by default, Anthropic/OpenAI one
> config change away), a pluggable vector store, evaluations, and tracing.

<p align="center"><em>Ships as a "personal twin" over your own notes; the same pipeline ingests a company knowledge base with only config + document changes — no code changes.</em></p>

---

## Why this project exists

Most "chat with your docs" demos are a single embedding call behind a text box. This one
is built to show the **engineering around** retrieval — the parts that decide whether a
RAG feature is trustworthy in production:

| Concern | How it's addressed |
| --- | --- |
| **Generic by construction** | A `DocumentSource` protocol + registry. A new source (S3, Confluence, Notion) is one module and a line of `sources.yaml`; chunking, retrieval, and answering never change. |
| **Provider independence** | Code references **roles** (`generator`, `embedder`, `verifier`), never model names. Switching Ollama → Anthropic/OpenAI is an edit to `models.yaml`, with a declared **fallback** per role. |
| **Pluggable storage** | One `VectorStore` interface. **Chroma** (embedded, zero-infra) by default; **pgvector** (Postgres) as an opt-in production backend. |
| **Grounded answers** | Every answer must cite its evidence with `[n]` markers; a verifier strips any citation that points at nothing — the anti-hallucination guardrail. |
| **Designed for extension** | Reranking and hybrid (BM25) retrieval are reserved as **no-op seams** (`reranker: provider: none`), so they drop in later without touching the retriever. |
| **Evaluation** | Deterministic metrics (citation validity, context recall, keyword recall, groundedness) unit-tested in CI, plus an LLM-judge runner over a golden dataset. |
| **Observability** | Structured, correlated logs; a step event per pipeline stage streamed over SSE; per-run JSONL traces; opt-in LangSmith. |
| **Production hygiene** | uv monorepo, strict `mypy`, `ruff`, `pytest` with a coverage gate, GitHub Actions CI, Docker Compose. |

## Architecture

```mermaid
flowchart LR
    subgraph Clients["Any chatbot frontend"]
        UI[SSE client]
    end

    subgraph API["FastAPI (twin_api)"]
        CHAT["/chat (SSE)"]
        ING["/ingest"]
        HLTH["/health"]
    end

    subgraph RAG["Pipeline (twin_rag)"]
        direction TB
        SRC[sources] --> CH[chunking] --> EMB[embeddings]
        EMB --> VS[(vector store)]
        Q[retriever] --> VS
        Q --> RR{rerank\nno-op seam}
        RR --> GEN[generation] --> CITE[citation verify]
    end

    subgraph Providers
        OLL[(Ollama)]
        CLOUD[(Anthropic / OpenAI)]
        STORE[(Chroma / pgvector)]
    end

    UI <-->|Server-Sent Events| CHAT
    CHAT --> Q
    ING --> SRC
    EMB & GEN --> OLL
    EMB & GEN -. models.yaml .-> CLOUD
    VS --> STORE
```

**The answer path, in words:** embed the question → nearest-neighbour search the vector
store → *(rerank — no-op today)* → generate an answer grounded in the numbered context →
verify every `[n]` citation → stream tokens + sources back over SSE.

## Quickstart

**Prerequisites:** Python 3.12 + [`uv`](https://docs.astral.sh/uv/), and an
[Ollama](https://ollama.com) install for local models.

```bash
# 0) Local models: a tool-capable generator + an embedding model
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text

# 1) Install the workspace
uv sync
cp .env.example .env

# 2) Index the sample corpus (data/sample_corpus) into Chroma
uv run twin ingest

# 3) Serve the API on :8000
uv run twin serve            # or: uv run uvicorn twin_api.main:create_app --factory --reload

# 4) Ask a question (streamed, cited answer)
curl -N -X POST localhost:8000/chat \
  -H 'content-type: application/json' \
  -d '{"question":"What does Mohit value in engineering?"}'
```

Point it at **your own** documents by editing `sources.yaml` (drop `.md`/`.txt`/`.pdf`
files under a directory) and re-running `uv run twin ingest`.

### Or with Docker

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose exec ollama ollama pull nomic-embed-text
docker compose run --rm ingest      # index the sample corpus
docker compose up api               # API on :8000
```

## API

| Method & path | Purpose |
| --- | --- |
| `POST /chat` | Ask a question; streams `trace` → `token` → `sources` → `done` events as SSE. Body: `{ "question": "...", "thread_id": null }` (`thread_id` reserved for future multi-turn memory). |
| `POST /ingest` | Index configured sources. Body: `{ "source": null, "reset": false }`. |
| `GET /health` | Config, tracing status, and vector-store reachability + document count. |

## Switching providers

Code never names a model — `models.yaml` maps **roles** to providers per **profile**:

```bash
# in .env
TWIN_MODELS_PROFILE=hosted          # use the 'hosted' profile in models.yaml
TWIN_ANTHROPIC_API_KEY=sk-ant-...
```

```bash
uv sync --extra anthropic           # install the provider SDK
uv run twin ingest && uv run twin serve
```

The `hosted` profile runs generation on Anthropic while keeping embeddings on Ollama, and
declares an Ollama **fallback** so a missing key degrades instead of crashing. Changing the
**embedder** is a migration, not a tweak — re-ingest into a fresh store, since vectors from
different embedding models must not be mixed.

Swap the vector store just as easily:

```bash
TWIN_VECTOR_STORE_BACKEND=pgvector
TWIN_DATABASE_URL=postgresql://twin:twin@localhost:5432/twin
uv sync --extra pgvector            # then: docker compose --profile postgres up -d postgres
```

## Evaluation

```bash
uv run python evals/run_evals.py --limit 3     # quick sweep
uv run python evals/run_evals.py               # full dataset + LLM judge
uv run python evals/run_evals.py --no-judge    # deterministic metrics only
```

Prints a per-question table (keyword recall, citation validity, context recall,
groundedness, and an LLM-judge relevance score) plus aggregates, and saves a JSON report
under `evals/results/`. The deterministic metrics live in
`packages/rag/src/twin_rag/evals/metrics.py` and are unit-tested, so scoring logic is
covered by CI even though full runs need a live model.

## Observability

- **Live** — each stage emits a structured `StepEvent`, forwarded to the client over SSE as
  `trace` events and to the logs.
- **Persisted** — with `TWIN_PERSIST_TRACES=true` (default), every run is written to
  `runs/<timestamp>-<slug>.jsonl`: a `run` header, one `step` line per stage, and a final
  `result`. No account needed — grep it, diff it, show it in a PR.
- **LangSmith (opt-in)** — set `TWIN_LANGSMITH_TRACING=true` + `TWIN_LANGSMITH_API_KEY` for a
  full per-call trace UI. `/health` reports whether it's active.

## Project structure

```
personal-twin/
  apps/api/            twin_api        — FastAPI: /chat (SSE), /ingest, /health; the `twin` CLI
  packages/
    config/            twin_config     — typed settings + models.yaml parser (fail-fast)
    observability/     twin_observability — logging, correlation ids, step events, JSONL traces
    rag/               twin_rag        — the pipeline:
                         sources/       DocumentSource protocol + local_dir + registry
                         chunking.py    structure-aware splitter, deterministic chunk ids
                         embeddings.py  provider-agnostic get_embedder()
                         vectorstore/   VectorStore protocol + chroma + pgvector + factory
                         retriever.py   dense retrieval + rerank seam
                         generation.py  grounded answer synthesis
                         citations.py   [n] citation verifier
                         registry.py    role → model resolution (fallback)
                         pipeline.py    IngestPipeline + AnswerPipeline
                         evals/         deterministic metrics
  models.yaml          role → provider mapping (profiles: local, hosted)
  sources.yaml         declared document sources
  evals/               golden dataset + LLM-judge runner
  compose.yaml         api + ollama (+ optional postgres profile)
```

## Design notes

- **Why deterministic Python orchestration, not a free-running agent?** The pipeline is a
  small, reproducible sequence of typed stages. That makes runs debuggable and every stage
  unit-testable in isolation, while the stages stay swappable behind protocols.
- **Why compute embeddings in the pipeline, not in the store?** So the embedder is a config
  choice independent of the storage backend — the store is a pure vector index.
- **Why SSE, not WebSockets?** The flow is one-directional (server → client) and SSE works
  with the browser's native `EventSource`, no client library required.

## Tech stack

**Backend:** Python 3.12 · FastAPI · LangChain · Ollama / Anthropic / OpenAI · Chroma /
pgvector · pydantic · structlog
**Tooling:** uv (workspace) · ruff · mypy (strict) · pytest + coverage · Docker · GitHub Actions

## License

MIT — see [LICENSE](./LICENSE).
