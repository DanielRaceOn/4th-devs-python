# -*- coding: utf-8 -*-

#   helpers.py

"""
### Description:
Shared eval helper utilities — mirrors experiments/lib/helpers.ts.

Provides:
  - ``confirm_experiment``       — interactive CLI confirmation prompt
  - ``as_array``                 — coerce any value to a list
  - ``to_case_input``            — extract id/message from a dataset input item
  - ``extract_tool_names``       — collect function_call names from session messages
  - ``compute_avg_score``        — compute average of named scores from item results
  - ``format_experiment_result`` — pretty-print an experiment result summary

Note: The JS ``createAvgScoreEvaluator`` is a higher-order factory that
returns a Langfuse ``RunEvaluator``.  In Python we don't have the JS
``dataset.runExperiment`` API, so experiments iterate over items manually.
``compute_avg_score`` provides the equivalent aggregation logic.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      experiments/lib/helpers.ts

"""

from typing import Any


def confirm_experiment(name: str, dataset_cases: int, description: str) -> None:
    """Interactive CLI prompt — abort with SystemExit if user declines.

    Prints a warning summary (in Polish, matching the original JS) and
    asks the user to type ``yes`` or ``y`` to proceed.

    Args:
        name: Experiment display name.
        dataset_cases: Number of test cases to process.
        description: Human-readable experiment description.
    """
    print("")
    print("⚠️  UWAGA: Zaraz zostanie uruchomiony eksperyment ewaluacyjny.")
    print(f"   Nazwa: {name}")
    print(f"   Opis:  {description}")
    print("")
    print("   Co się stanie:")
    print(f"   • Dla każdego z {dataset_cases} przypadków testowych zostanie wysłane zapytanie do LLM")
    print("   • Każde zapytanie zużywa tokeny (i generuje koszty)")
    print("   • Wyniki zostaną zapisane w Langfuse (dataset + experiment)")
    print("")

    answer = input("   Czy chcesz kontynuować? (yes/y): ").strip().lower()
    if answer not in ("yes", "y"):
        print("   Przerwano.")
        raise SystemExit(0)

    print("")


def as_array(value: Any) -> list[Any]:
    """Coerce any value to a list — return as-is if already a list.

    Args:
        value: Any value.

    Returns:
        The value if it is already a list, otherwise an empty list.
    """
    return value if isinstance(value, list) else []


def to_case_input(item: Any) -> dict[str, str]:
    """Extract ``id`` and ``message`` from a dataset input item.

    Args:
        item: Raw input value from a dataset item.

    Returns:
        Dict with ``id`` (str) and ``message`` (str), defaulting to
        ``"unknown"`` / ``""`` for missing or non-string values.
    """
    if not isinstance(item, dict):
        return {"id": "unknown", "message": ""}
    return {
        "id": item.get("id") if isinstance(item.get("id"), str) else "unknown",
        "message": item.get("message") if isinstance(item.get("message"), str) else "",
    }


def extract_tool_names(messages: list[dict[str, Any]]) -> list[str]:
    """Collect tool names from ``function_call`` output items in a session.

    In Responses API format, tool calls appear as items with
    ``type == "function_call"`` in the session messages.

    Args:
        messages: List of session message dicts.

    Returns:
        List of tool name strings (may contain duplicates if called multiple
        times).
    """
    return [
        msg["name"]
        for msg in messages
        if isinstance(msg, dict)
        and msg.get("type") == "function_call"
        and isinstance(msg.get("name"), str)
    ]


def compute_avg_score(
    item_results: list[dict[str, Any]],
    score_name: str,
) -> dict[str, Any]:
    """Compute the average of a named score across all item results.

    Equivalent to JS ``createAvgScoreEvaluator(scoreName)`` applied after
    all items have been evaluated.

    Args:
        item_results: List of dicts, each containing an ``evaluations`` list
                      of ``{"name": str, "value": float}`` dicts.
        score_name: The evaluation metric name to average.

    Returns:
        Dict with ``name``, ``value``, and ``comment`` keys.
    """
    scores: list[float] = [
        ev["value"]
        for item in item_results
        for ev in item.get("evaluations", [])
        if ev.get("name") == score_name and isinstance(ev.get("value"), (int, float))
    ]

    if not scores:
        return {
            "name": f"avg_{score_name}",
            "value": 0.0,
            "comment": f"No per-item {score_name} scores produced",
        }

    avg = sum(scores) / len(scores)
    return {
        "name": f"avg_{score_name}",
        "value": avg,
        "comment": f"{avg * 100:.1f}% across {len(scores)} items",
    }


def format_experiment_result(
    experiment_name: str,
    item_results: list[dict[str, Any]],
    run_evaluators: list[dict[str, Any]],
) -> str:
    """Format an experiment result as a human-readable string.

    Equivalent to JS ``result.format({ includeItemResults: true })``.

    Args:
        experiment_name: Display name for the experiment.
        item_results: Per-item result dicts (with ``id`` and ``evaluations``).
        run_evaluators: Aggregate scores (output of ``compute_avg_score``).

    Returns:
        A formatted multi-line string summary.
    """
    lines = [
        "",
        f"=== {experiment_name} ===",
        f"Items: {len(item_results)}",
        "",
        "Aggregate scores:",
    ]
    for agg in run_evaluators:
        lines.append(f"  {agg['name']}: {agg['value']:.3f}  ({agg['comment']})")

    lines.append("")
    lines.append("Per-item results:")
    for item in item_results:
        item_id = item.get("id", "?")
        evals = item.get("evaluations", [])
        scores_str = ", ".join(
            f"{e['name']}={e['value']:.2f}"
            for e in evals
            if isinstance(e.get("value"), (int, float))
        )
        comment_str = "; ".join(
            e["comment"]
            for e in evals
            if e.get("comment")
        )
        lines.append(f"  [{item_id}] {scores_str}")
        if comment_str:
            lines.append(f"    {comment_str}")

    lines.append("")
    return "\n".join(lines)
