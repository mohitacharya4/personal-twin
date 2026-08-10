"""Opt-in LangSmith tracing.

The system is fully functional without it. When enabled, this bridges typed settings
into the environment variables LangChain reads (pydantic-settings loads ``.env`` but
does not export to ``os.environ``), so every LLM call and chain step shows up in the
LangSmith UI with no changes to pipeline code.
"""

from __future__ import annotations

import os

from twin_config import Settings

from twin_observability.logging import get_logger

log = get_logger(__name__)


def configure_langsmith(settings: Settings) -> bool:
    """Enable LangSmith from typed settings, if requested. No-op unless on and keyed.

    Returns True when tracing was activated, else False.
    """
    if not settings.tracing_enabled or settings.langsmith_api_key is None:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
    log.info("langsmith.enabled", project=settings.langsmith_project)
    return True
