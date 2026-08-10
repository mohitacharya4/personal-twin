"""Prompt templates for grounded answering.

The contract the generator must honour: answer *only* from the numbered context, cite
every claim with the matching ``[n]``, and say when the context doesn't cover the
question rather than inventing an answer. Citation discipline here is what makes the
downstream verifier (:mod:`twin_rag.citations`) meaningful.
"""

from __future__ import annotations

from twin_rag.models import ScoredChunk

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
numbered context provided. Follow these rules exactly:

1. Ground every statement in the context. Do not use outside knowledge.
2. Cite each claim with the number of the context that supports it, like [1] or [2].
   Cite the specific source(s) for each sentence; do not dump all citations at the end.
3. If the context does not contain the answer, say so plainly: "I don't have information \
about that in my knowledge base." Do not guess.
4. Be concise and direct. Prefer the user's own words and framing where the context uses them.
"""


def build_context_block(contexts: list[ScoredChunk]) -> str:
    """Render retrieved chunks as a numbered, citable block."""
    blocks = []
    for marker, scored in enumerate(contexts, start=1):
        chunk = scored.chunk
        header = f"[{marker}] {chunk.title}".rstrip()
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def build_user_prompt(question: str, contexts: list[ScoredChunk]) -> str:
    """The user turn: the numbered context followed by the question."""
    context_block = build_context_block(contexts) or "(no context retrieved)"
    return f"Context:\n{context_block}\n\nQuestion: {question}\n\nAnswer (with [n] citations):"
