"""Evaluate the answer pipeline against the golden dataset.

Runs each question through the real pipeline, scores the answer with the deterministic
metrics (:mod:`twin_rag.evals.metrics`), optionally adds an LLM-judge relevance score, and
writes a per-question table plus aggregates to ``evals/results/<timestamp>.json``.

Prerequisites: a running Ollama (or a configured hosted profile) and an ingested corpus
(``uv run twin ingest``). The deterministic metrics themselves are unit-tested in CI; this
runner needs a live model, so it is a manual/integration tool, not a CI step.

    uv run python evals/run_evals.py --limit 3      # quick sweep
    uv run python evals/run_evals.py                # full dataset + LLM judge
    uv run python evals/run_evals.py --no-judge     # deterministic metrics only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_DATASET = _ROOT / "evals" / "dataset.jsonl"
_RESULTS_DIR = _ROOT / "evals" / "results"


def load_cases(path: Path, limit: int | None) -> list[Any]:
    from twin_rag.evals import EvalCase

    cases = [
        EvalCase.model_validate_json(line)
        for line in path.read_text("utf-8").splitlines()
        if line.strip()
    ]
    return cases[:limit] if limit else cases


def judge_relevance(model: Any, question: str, answer_text: str, gist: str | None) -> float | None:
    """Ask the verifier model to rate answer relevance 1-5; return it normalised to [0, 1]."""
    from langchain_core.messages import HumanMessage, SystemMessage

    reference = f"\nReference answer: {gist}" if gist else ""
    prompt = (
        f"Question: {question}\nAnswer: {answer_text}{reference}\n\n"
        "On a scale of 1 to 5, how well does the Answer address the Question "
        "(5 = fully and accurately, 1 = not at all)? Respond with a single integer."
    )
    try:
        response = model.invoke(
            [SystemMessage(content="You are a strict grader."), HumanMessage(content=prompt)]
        )
        match = re.search(r"[1-5]", str(response.content))
        if match is None:
            return None
        return (int(match.group()) - 1) / 4
    except Exception as exc:
        print(f"  (judge failed: {exc})")
        return None


def run(limit: int | None, profile: str | None, use_judge: bool) -> int:
    if profile:
        os.environ["TWIN_MODELS_PROFILE"] = profile

    from twin_api.assembly import build_answer_pipeline, build_registry
    from twin_config import get_settings, reset_settings_cache
    from twin_observability import configure_logging
    from twin_rag.evals import score_answer

    reset_settings_cache()
    settings = get_settings()
    configure_logging(level="WARNING", json_output=False)

    cases = load_cases(_DATASET, limit)
    registry = build_registry(settings)
    pipeline = build_answer_pipeline(settings, registry=registry)
    judge = registry.chat_model("verifier") if use_judge else None

    print(f"\nEvaluating {len(cases)} case(s) — profile '{registry.profile}'\n")
    header = f"{'question':<52} {'kw':>5} {'cite':>5} {'ctx':>5} {'grnd':>5} {'judge':>6}"
    print(header)
    print("-" * len(header))

    rows: list[dict[str, Any]] = []
    started = time.time()
    for case in cases:
        answer = pipeline.run(case.question)
        scores = score_answer(answer, case)
        judge_score = (
            judge_relevance(judge, case.question, answer.text, case.answer_gist)
            if judge is not None
            else None
        )
        rows.append(
            {
                "question": case.question,
                **scores.model_dump(),
                "judge_relevance": judge_score,
                "answer": answer.text,
                "unsupported_markers": answer.unsupported_markers,
            }
        )
        judge_cell = f"{judge_score:.2f}" if judge_score is not None else "  -  "
        print(
            f"{case.question[:52]:<52} {scores.keyword_recall:>5.2f} "
            f"{scores.citation_validity:>5.2f} {scores.context_recall:>5.2f} "
            f"{scores.groundedness:>5.2f} {judge_cell:>6}"
        )

    aggregates = _aggregate(rows)
    print("\nAggregates:")
    for name, value in aggregates.items():
        print(f"  {name:<18} {value:.3f}")

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = _RESULTS_DIR / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    out.write_text(
        json.dumps(
            {
                "profile": registry.profile,
                "duration_s": round(time.time() - started, 1),
                "aggregates": aggregates,
                "results": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {out}")
    return 0


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    metrics = ["keyword_recall", "citation_validity", "context_recall", "groundedness"]
    result = {m: statistics.mean(r[m] for r in rows) for m in metrics}
    judged = [r["judge_relevance"] for r in rows if r["judge_relevance"] is not None]
    if judged:
        result["judge_relevance"] = statistics.mean(judged)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the Personal Twin answer pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases")
    parser.add_argument("--profile", default=None, help="Override the models.yaml profile")
    parser.add_argument("--no-judge", action="store_true", help="Skip the LLM-judge metric")
    args = parser.parse_args()
    return run(args.limit, args.profile, not args.no_judge)


if __name__ == "__main__":
    raise SystemExit(main())
