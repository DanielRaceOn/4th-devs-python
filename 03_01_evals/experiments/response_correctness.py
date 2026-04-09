# -*- coding: utf-8 -*-

#   response_correctness.py

"""
### Description:
Response-correctness evaluation experiment — mirrors
experiments/response-correctness.ts.

Evaluates whether the Alice agent's final answer is factually correct for
three categories of expected output:
  - ``exact_number``         — the response contains the expected number
  - ``contains_iso_timestamp`` — the response contains an ISO 8601 timestamp
  - ``relevance``            — the response is on-topic for the given topic

Metrics per item:
  - ``response_correctness`` — 0 or 1 based on category rule
  - ``has_response``         — 1 if the agent produced any text, 0 otherwise

Usage:
    .venv/Scripts/python 03_01_evals/experiments/response_correctness.py

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      experiments/response-correctness.ts

"""

import asyncio
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Ensure the module root and project root are in the path
_EXPERIMENTS_DIR = Path(__file__).parent
_MODULE_ROOT = _EXPERIMENTS_DIR.parent
_PROJECT_ROOT = _MODULE_ROOT.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_MODULE_ROOT))

from dotenv import load_dotenv

load_dotenv(_MODULE_ROOT / ".env")

from src.types import Session  # noqa: E402
from src.agent.run import run_agent  # noqa: E402
from experiments.lib.context import bootstrap  # noqa: E402
from experiments.lib.dataset import (  # noqa: E402
    DatasetItemSeed,
    ensure_dataset,
    load_json_file,
    sync_dataset_items,
)
from experiments.lib.helpers import (  # noqa: E402
    as_array,
    compute_avg_score,
    confirm_experiment,
    format_experiment_result,
    to_case_input,
)

DATASET_PATH = _MODULE_ROOT / "experiments" / "datasets" / "response-correctness.synthetic.json"
DATASET_NAME = "03_01_evals/response-correctness-synthetic"
EXPERIMENT_NAME = "03_01 Response Correctness Eval"

# ---------------------------------------------------------------------------
# Dataset parsing
# ---------------------------------------------------------------------------


def _parse_dataset(raw: Any) -> list[dict[str, Any]]:
    """Parse and validate raw JSON dataset into correctness test cases.

    Args:
        raw: Parsed JSON value (should be a list of objects).

    Returns:
        List of validated test case dicts.
    """
    cases: list[dict[str, Any]] = []
    for item in as_array(raw):
        if not isinstance(item, dict):
            continue
        c_id = item.get("id")
        message = item.get("message")
        expect = item.get("expect")
        if (
            not isinstance(c_id, str)
            or not isinstance(message, str)
            or not isinstance(expect, dict)
            or not isinstance(expect.get("type"), str)
        ):
            continue
        cases.append(item)

    return cases


def _to_seeds(cases: list[dict[str, Any]]) -> list[DatasetItemSeed]:
    """Convert test cases to Langfuse dataset item seeds."""
    return [
        DatasetItemSeed(
            id=f"03_01_evals_rc_{c['id']}",
            input={"id": c["id"], "message": c["message"]},
            expected_output=c["expect"],
            metadata={"source": "synthetic", "caseId": c["id"]},
        )
        for c in cases
    ]


# ---------------------------------------------------------------------------
# Scoring rules
# ---------------------------------------------------------------------------

_ISO_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_GREETING_PATTERN = re.compile(
    r"\b(hello|hi|hey|howdy|greetings|good\s+(morning|afternoon|evening|day)|welcome)\b",
    re.IGNORECASE,
)


def _extract_numbers(text: str) -> list[float]:
    """Extract all numbers from a response string."""
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    result = []
    for m in matches:
        try:
            result.append(float(m))
        except ValueError:
            pass
    return result


def _score_exact_number(response: str, expected: float) -> dict[str, Any]:
    """Score whether the response contains the expected number (±0.01)."""
    numbers = _extract_numbers(response)
    found = any(abs(n - expected) < 0.01 for n in numbers)
    if found:
        return {"value": 1, "comment": f"Found expected value {expected} in response"}
    return {"value": 0, "comment": f"Expected {expected}, found numbers: [{', '.join(str(n) for n in numbers)}]"}


def _score_timestamp(response: str) -> dict[str, Any]:
    """Score whether the response contains a valid ISO 8601 timestamp."""
    if _ISO_PATTERN.search(response):
        return {"value": 1, "comment": "Response contains valid ISO timestamp"}
    return {"value": 0, "comment": "No ISO timestamp found in response"}


def _score_relevance(response: str, topic: str) -> dict[str, Any]:
    """Score whether the response is topically relevant."""
    topic_lower = topic.lower()

    if "greeting" in topic_lower:
        if _GREETING_PATTERN.search(response):
            return {"value": 1, "comment": "Response contains a greeting"}
        return {"value": 0, "comment": "No greeting detected in response"}

    response_lower = response.lower()
    keywords = topic_lower.split()
    matched = [kw for kw in keywords if kw in response_lower]

    if matched:
        return {"value": 1, "comment": f"On-topic: matched [{', '.join(matched)}]"}
    return {"value": 0, "comment": f"Off-topic: expected keywords from \"{topic}\", matched none"}


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _evaluate_correctness(
    input_val: Any,
    output_val: Any,
    expected_output: Any,
) -> list[dict[str, Any]]:
    """Score a single item's response correctness.

    Args:
        input_val: Dataset item input dict (``{id, message}``).
        output_val: Task output dict (``{response, ...}``).
        expected_output: Expected behaviour dict from the dataset.

    Returns:
        List of score dicts with ``name``, ``value``, and ``comment`` keys.
    """
    input_case = to_case_input(input_val)
    response = (
        str(output_val.get("response", ""))
        if isinstance(output_val, dict)
        else ""
    )
    has_response = 1 if response else 0

    if not isinstance(expected_output, dict):
        return [{"name": "response_correctness", "value": 0, "comment": "Missing expectedOutput"}]

    expect_type = expected_output.get("type")

    if expect_type == "exact_number":
        expected_val = expected_output.get("value")
        if not isinstance(expected_val, (int, float)):
            return [{"name": "response_correctness", "value": 0, "comment": "Invalid exact_number value"}]
        score = _score_exact_number(response, float(expected_val))
    elif expect_type == "contains_iso_timestamp":
        score = _score_timestamp(response)
    elif expect_type == "relevance":
        topic = expected_output.get("topic", "")
        score = _score_relevance(response, str(topic))
    else:
        return [{"name": "response_correctness", "value": 0, "comment": f"Unknown expect type: {expect_type}"}]

    return [
        {
            "name": "response_correctness",
            "value": score["value"],
            "comment": f"[{input_case['id']}] {score['comment']}",
        },
        {"name": "has_response", "value": float(has_response), "comment": ""},
    ]


# ---------------------------------------------------------------------------
# Task runner
# ---------------------------------------------------------------------------


async def _run_task(ctx: Any, item_input: Any) -> dict[str, Any]:
    """Run the agent on a single dataset item.

    Args:
        ctx: ``ExperimentContext`` with adapter and logger.
        item_input: Dataset item input value (``{id, message}``).

    Returns:
        Output dict with ``id``, ``message``, ``response``, ``turns``,
        and ``usageTotal``.
    """
    input_case = to_case_input(item_input)
    session = Session(id=f"eval-rc-{input_case['id']}-{int(time.time() * 1000)}")

    run = await run_agent(
        adapter=ctx.adapter,
        logger=ctx.logger,
        session=session,
        message=input_case["message"],
    )

    return {
        "id": input_case["id"],
        "message": input_case["message"],
        "response": run.response,
        "turns": run.turns,
        "usageTotal": run.usage.total or 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Load dataset, confirm, bootstrap, run experiment, print results."""
    file_result = load_json_file(DATASET_PATH)
    if not file_result.ok:
        raise RuntimeError(f"Dataset load failed: {file_result.error}")

    cases = _parse_dataset(file_result.value)
    if not cases:
        raise RuntimeError("No valid cases in dataset")

    confirm_experiment(
        name="Response Correctness Eval",
        dataset_cases=len(cases),
        description=(
            "Sprawdza poprawność odpowiedzi agenta: dokładne liczby, "
            "znaczniki czasu ISO, trafność tematyczną."
        ),
    )

    ctx = await bootstrap("response_correctness")

    try:
        # Ensure dataset and sync items
        ensure_dataset(
            ctx.langfuse,
            name=DATASET_NAME,
            description="Synthetic response-correctness evaluation dataset",
            logger=ctx.logger,
            metadata={
                "source": str(DATASET_PATH),
                "kind": "synthetic",
                "domain": "response-correctness",
            },
        )
        seeds = _to_seeds(cases)
        sync_dataset_items(ctx.langfuse, DATASET_NAME, seeds, ctx.logger)

        # Retrieve dataset items and run tasks with concurrency=2
        dataset = ctx.langfuse.get_dataset(DATASET_NAME)
        semaphore = asyncio.Semaphore(2)

        item_results: list[dict[str, Any]] = []

        async def _process_item(lf_item: Any) -> None:
            async with semaphore:
                output = await _run_task(ctx, lf_item.input)
                evaluations = _evaluate_correctness(
                    lf_item.input, output, lf_item.expected_output
                )
                with lf_item.observe(run_name=EXPERIMENT_NAME) as root:
                    root.update(output=output)
                    for ev in evaluations:
                        root.score(name=ev["name"], value=ev["value"], comment=ev.get("comment"))

                item_results.append({"id": output["id"], "evaluations": evaluations})

        await asyncio.gather(*[_process_item(item) for item in dataset.items])

        # Aggregate scores
        agg = compute_avg_score(item_results, "response_correctness")
        print(format_experiment_result(EXPERIMENT_NAME, item_results, [agg]))

    finally:
        await ctx.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
