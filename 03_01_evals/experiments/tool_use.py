# -*- coding: utf-8 -*-

#   tool_use.py

"""
### Description:
Tool-use evaluation experiment — mirrors experiments/tool-use.ts.

Evaluates whether the Alice agent correctly selects and invokes the
``get_current_time`` and ``sum_numbers`` tools for synthetic test cases.

Metrics per item:
  - ``tool_use_overall``                — average of the four sub-metrics
  - ``tool_use_decision_accuracy``      — correct decision to use / skip tools
  - ``tool_use_required_tools_accuracy`` — required tools were called
  - ``tool_use_forbidden_tools_accuracy`` — forbidden tools were NOT called
  - ``tool_use_call_count_accuracy``     — call count within min/max bounds

Usage:
    .venv/Scripts/python 03_01_evals/experiments/tool_use.py

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      experiments/tool-use.ts

"""

import asyncio
import os
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
    extract_tool_names,
    format_experiment_result,
    to_case_input,
)

DATASET_PATH = _MODULE_ROOT / "experiments" / "datasets" / "tool-use.synthetic.json"
DATASET_NAME = "03_01_evals/tool-use-synthetic"
EXPERIMENT_NAME = "03_01 Tool Use Eval"

# ---------------------------------------------------------------------------
# Dataset parsing
# ---------------------------------------------------------------------------


def _parse_dataset(raw: Any) -> list[dict[str, Any]]:
    """Parse and validate raw JSON dataset into tool-use test cases.

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
        if not isinstance(c_id, str) or not isinstance(message, str):
            continue
        if not isinstance(expect, dict) or not isinstance(expect.get("shouldUseTools"), bool):
            continue

        required_tools = [v for v in as_array(expect.get("requiredTools")) if isinstance(v, str)]
        forbidden_tools = [v for v in as_array(expect.get("forbiddenTools")) if isinstance(v, str)]

        cases.append({
            "id": c_id,
            "message": message,
            "expect": {
                "shouldUseTools": expect["shouldUseTools"],
                "requiredTools": required_tools,
                "forbiddenTools": forbidden_tools,
                "minToolCalls": expect.get("minToolCalls"),
                "maxToolCalls": expect.get("maxToolCalls"),
            },
        })

    return cases


def _to_seeds(cases: list[dict[str, Any]]) -> list[DatasetItemSeed]:
    """Convert test cases to Langfuse dataset item seeds.

    Args:
        cases: Validated test case dicts.

    Returns:
        List of ``DatasetItemSeed`` objects ready for Langfuse.
    """
    return [
        DatasetItemSeed(
            id=f"03_01_evals_tool_use_{c['id']}",
            input={"id": c["id"], "message": c["message"]},
            expected_output=c["expect"],
            metadata={"source": "synthetic", "caseId": c["id"]},
        )
        for c in cases
    ]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _evaluate_tool_use(
    input_val: Any,
    output_val: Any,
    expected_output: Any,
) -> list[dict[str, Any]]:
    """Score a single item's tool-use behaviour against expectations.

    Args:
        input_val: Dataset item input dict (``{id, message}``).
        output_val: Task output dict (``{toolNames, ...}``).
        expected_output: Expected behaviour dict from the dataset.

    Returns:
        List of score dicts with ``name``, ``value``, and ``comment`` keys.
    """
    input_case = to_case_input(input_val)

    # Extract expectations
    expect: dict[str, Any] = expected_output if isinstance(expected_output, dict) else {}
    should_use = bool(expect.get("shouldUseTools", False))
    required = [v for v in as_array(expect.get("requiredTools")) if isinstance(v, str)]
    forbidden = [v for v in as_array(expect.get("forbiddenTools")) if isinstance(v, str)]
    min_calls: Optional[int] = expect.get("minToolCalls")
    max_calls: Optional[int] = expect.get("maxToolCalls")

    # Extract tool names from output
    output_obj: dict[str, Any] = output_val if isinstance(output_val, dict) else {}
    tool_names = [v for v in as_array(output_obj.get("toolNames")) if isinstance(v, str)]
    unique = set(tool_names)
    count = len(tool_names)

    # decision: did the agent use tools when it should (or not) have?
    decision = int(should_use == (count > 0))

    # required tools were all called
    required_ok = int(all(t in unique for t in required)) if required else 1

    # forbidden tools were NOT called
    forbidden_ok = int(all(t not in unique for t in forbidden)) if forbidden else 1

    # call count within bounds
    min_ok = (count >= min_calls) if min_calls is not None else True
    max_ok = (count <= max_calls) if max_calls is not None else True
    count_ok = int(min_ok and max_ok)

    overall = (decision + required_ok + forbidden_ok + count_ok) / 4

    return [
        {
            "name": "tool_use_overall",
            "value": overall,
            "comment": f"[{input_case['id']}] tools=[{', '.join(tool_names)}]",
        },
        {"name": "tool_use_decision_accuracy", "value": float(decision), "comment": ""},
        {"name": "tool_use_required_tools_accuracy", "value": float(required_ok), "comment": ""},
        {"name": "tool_use_forbidden_tools_accuracy", "value": float(forbidden_ok), "comment": ""},
        {"name": "tool_use_call_count_accuracy", "value": float(count_ok), "comment": ""},
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
        ``usageTotal``, ``toolCalls``, and ``toolNames``.
    """
    input_case = to_case_input(item_input)
    session = Session(id=f"eval-{input_case['id']}-{int(time.time() * 1000)}")

    run = await run_agent(
        adapter=ctx.adapter,
        logger=ctx.logger,
        session=session,
        message=input_case["message"],
    )

    tool_names = extract_tool_names(session.messages)
    return {
        "id": input_case["id"],
        "message": input_case["message"],
        "response": run.response,
        "turns": run.turns,
        "usageTotal": run.usage.total or 0,
        "toolCalls": len(tool_names),
        "toolNames": tool_names,
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
        name="Tool Use Eval",
        dataset_cases=len(cases),
        description=(
            "Sprawdza, czy agent poprawnie wybiera i wywołuje narzędzia "
            "(get_current_time, sum_numbers) dla syntetycznych przypadków testowych."
        ),
    )

    ctx = await bootstrap("tool_use")

    try:
        # Ensure dataset and sync items
        ensure_dataset(
            ctx.langfuse,
            name=DATASET_NAME,
            description="Synthetic tool-use evaluation dataset",
            logger=ctx.logger,
            metadata={"source": str(DATASET_PATH), "kind": "synthetic", "domain": "tool-use"},
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
                evaluations = _evaluate_tool_use(
                    lf_item.input, output, lf_item.expected_output
                )
                # Record the run in Langfuse using the dataset item's observe context
                with lf_item.observe(run_name=EXPERIMENT_NAME) as root:
                    root.update(output=output)
                    for ev in evaluations:
                        root.score(name=ev["name"], value=ev["value"], comment=ev.get("comment"))

                item_results.append({"id": output["id"], "evaluations": evaluations})

        await asyncio.gather(*[_process_item(item) for item in dataset.items])

        # Aggregate scores
        agg = compute_avg_score(item_results, "tool_use_overall")
        print(format_experiment_result(EXPERIMENT_NAME, item_results, [agg]))

    finally:
        await ctx.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
