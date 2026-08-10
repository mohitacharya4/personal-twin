# syntax=docker/dockerfile:1.9
#
# One Python image for both roles; the *command* selects it (`api` | `ingest`).
# No role-specific config is baked in — it comes from the environment.

# ---------------------------------------------------------------------------
# Builder — resolve and install dependencies into a self-contained venv.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Manifests first so dependency layers stay cached when only source changes.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY packages/config/pyproject.toml packages/config/
COPY packages/observability/pyproject.toml packages/observability/
COPY packages/rag/pyproject.toml packages/rag/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-workspace --no-dev

COPY packages/ packages/
COPY apps/api/ apps/api/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------------------------------------------------------------------------
# Runtime — slim, non-root, no build tooling.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# curl is required by HEALTHCHECK; nothing else is installed.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home /app --no-create-home app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder --chown=app:app /app /app
COPY --chown=app:app models.yaml sources.yaml ./
COPY --chown=app:app data/sample_corpus/ data/sample_corpus/
COPY --chown=app:app docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /app/data/chroma && chown app:app /app/data/chroma

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["api"]
