"""Application settings — typed, validated at boot, fail-fast.

A single ``Settings`` object is the only place environment variables are read; the
rest of the codebase depends on it rather than calling ``os.getenv`` ad hoc. A
missing or invalid required variable raises :class:`ConfigError` with a message that
names the offending environment variable — the process MUST NOT start half-configured.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when configuration is missing or invalid. Fatal by design."""


class AppEnv(StrEnum):
    """Deployment environment. Controls dev-only affordances, never behaviour."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


VectorStoreBackend = Literal["chroma", "pgvector"]


class Settings(BaseSettings):
    """The single typed view of every environment variable Personal Twin reads.

    Add a field here — never an ``os.getenv`` call elsewhere. Every field is
    documented in ``.env.example``. All variables use the ``TWIN_`` prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="TWIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Core ------------------------------------------------------------
    app_env: AppEnv = AppEnv.DEV
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- HTTP ------------------------------------------------------------
    api_host: str = "0.0.0.0"  # noqa: S104 — containers bind all interfaces by design
    api_port: Annotated[int, Field(ge=1, le=65535)] = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- Config file locations -------------------------------------------
    models_config_path: Path = Path("models.yaml")
    sources_config_path: Path = Path("sources.yaml")
    #: Which profile in models.yaml to use. None → the file's own ``default_profile``.
    models_profile: str | None = None

    # --- Data locations --------------------------------------------------
    data_dir: Path = Path("data")

    # --- LLM / embedding providers (keys optional; only needed per profile) --
    ollama_base_url: str = "http://localhost:11434"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # --- Vector store ----------------------------------------------------
    vector_store_backend: VectorStoreBackend = "chroma"
    chroma_path: Path = Path("data/chroma")
    #: Only required when ``vector_store_backend == "pgvector"``.
    database_url: str | None = None

    # --- Chunking / retrieval knobs --------------------------------------
    chunk_size: Annotated[int, Field(ge=100, le=4000)] = 800
    chunk_overlap: Annotated[int, Field(ge=0, le=1000)] = 120
    retrieval_top_k: Annotated[int, Field(ge=1, le=50)] = 5

    # --- Observability ---------------------------------------------------
    persist_traces: bool = True
    trace_dir: Path = Path("runs")

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "personal-twin"
    langsmith_endpoint: str | None = None

    @field_validator(
        "anthropic_api_key",
        "openai_api_key",
        "database_url",
        "models_profile",
        "langsmith_api_key",
        "langsmith_endpoint",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        """Treat empty/whitespace env values (e.g. ``TWIN_OPENAI_API_KEY=``) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_below_size(cls, value: int, info: object) -> int:
        """Overlap must be smaller than the chunk size or chunking never advances."""
        # ``info.data`` carries already-validated fields; chunk_size is declared first.
        size = getattr(info, "data", {}).get("chunk_size")
        if size is not None and value >= size:
            msg = f"chunk_overlap ({value}) must be smaller than chunk_size ({size})"
            raise ValueError(msg)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list (comma-separated in the env var)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tracing_enabled(self) -> bool:
        """LangSmith tracing is opt-in; the system is fully functional without it."""
        return self.langsmith_tracing and self.langsmith_api_key is not None


def load_settings() -> Settings:
    """Build settings from the environment, turning validation failure into a fatal error.

    Pydantic's raw ``ValidationError`` names fields, not environment variables. Operators
    set environment variables, so that is what the message must name.
    """
    try:
        return Settings()  # values come from the environment
    except ValidationError as exc:
        problems = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            env_var = f"TWIN_{field.upper()}"
            problems.append(f"  - {env_var}: {error['msg']}")
        detail = "\n".join(problems)
        msg = (
            f"Invalid Personal Twin configuration ({len(problems)} problem(s)). "
            f"See .env.example for the required variables.\n{detail}"
        )
        raise ConfigError(msg) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, resolved once at boot."""
    return load_settings()


def reset_settings_cache() -> None:
    """Clear the cached settings. For tests only."""
    get_settings.cache_clear()
