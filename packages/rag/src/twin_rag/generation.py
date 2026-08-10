"""Grounded answer synthesis — call the generator over the numbered context.

Returns the raw answer text and token usage; citation *verification* is a separate step
(:mod:`twin_rag.citations`) so generation stays a thin, provider-agnostic model call.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from twin_rag.models import ScoredChunk
from twin_rag.prompts import SYSTEM_PROMPT, build_user_prompt


def generate_answer(
    llm: BaseChatModel, question: str, contexts: list[ScoredChunk]
) -> tuple[str, dict[str, Any]]:
    """Produce a grounded answer from ``contexts``. Returns ``(text, usage)``."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(question, contexts)),
    ]
    response = llm.invoke(messages)
    return _content_to_text(response.content), _usage(response)


def _content_to_text(content: Any) -> str:
    """Coerce a message's content to plain text (some providers return content blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block["text"] if isinstance(block, dict) and "text" in block else str(block)
            for block in content
        ]
        return "".join(parts).strip()
    return str(content).strip()


def _usage(response: Any) -> dict[str, Any]:
    """Pull token counts off the response if the provider reported them."""
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        return {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
    return {}
