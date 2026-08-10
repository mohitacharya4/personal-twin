"""Provider-agnostic chat-model factory.

The pipeline talks to ``get_llm()`` and never imports a concrete provider. Switching a
local Ollama model for a cloud one is a config change — the returned object is always a
LangChain ``BaseChatModel``, so ``.invoke()`` / ``.bind_tools()`` behave identically
downstream. Phase 4's ModelRegistry calls this per role (generator, verifier, …) with the
provider/model resolved from ``models.yaml``.
"""

from __future__ import annotations

from typing import Literal, cast

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr
from twin_config import Settings, get_settings

LLMProvider = Literal["ollama", "anthropic", "openai"]

DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_llm(
    *,
    provider: LLMProvider = "ollama",
    model: str | None = None,
    temperature: float = 0.1,
    settings: Settings | None = None,
) -> BaseChatModel:
    """Build a chat model for the requested provider.

    Args:
        provider: Which backend to use.
        model: Override the provider's default model.
        temperature: Sampling temperature.
        settings: Injected settings (defaults to the cached process settings).
    """
    settings = settings or get_settings()
    if provider == "ollama":
        return _build_ollama(settings, model, temperature)
    if provider == "anthropic":
        return _build_anthropic(settings, model, temperature)
    if provider == "openai":
        return _build_openai(settings, model, temperature)
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def _build_ollama(settings: Settings, model: str | None, temperature: float) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    chat = ChatOllama(
        model=model or DEFAULT_OLLAMA_MODEL,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )
    return cast(BaseChatModel, chat)


def _build_anthropic(settings: Settings, model: str | None, temperature: float) -> BaseChatModel:
    key = settings.anthropic_api_key
    if not key:
        raise ValueError(
            "LLM provider 'anthropic' requires TWIN_ANTHROPIC_API_KEY. "
            "Set it in .env or use the 'ollama' provider."
        )
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "The 'anthropic' extra is not installed. Run: uv sync --extra anthropic"
        ) from exc

    chat = ChatAnthropic(
        model_name=model or DEFAULT_ANTHROPIC_MODEL,
        api_key=SecretStr(key),
        temperature=temperature,
        timeout=60,
        stop=None,
    )
    return cast(BaseChatModel, chat)


def _build_openai(settings: Settings, model: str | None, temperature: float) -> BaseChatModel:
    key = settings.openai_api_key
    if not key:
        raise ValueError(
            "LLM provider 'openai' requires TWIN_OPENAI_API_KEY. "
            "Set it in .env or use the 'ollama' provider."
        )
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "The 'openai' extra is not installed. Run: uv sync --extra openai"
        ) from exc

    chat = ChatOpenAI(
        model=model or DEFAULT_OPENAI_MODEL,
        api_key=SecretStr(key),
        temperature=temperature,
        timeout=60,
    )
    return cast(BaseChatModel, chat)
