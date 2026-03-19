# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for the Daily Ops Generator. Prompts the user for confirmation
before running the orchestrator agent, then prints the final result.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      src/index.ts


"""

import asyncio
import logging
import sys
from datetime import date

from src.agent import run_agent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEMO_FILE = "02_04_ops/demo/example.md"


async def confirm_run() -> None:
    """Prompt the user for confirmation before consuming tokens.

    Runs the blocking ``input()`` call in an executor to keep the asyncio
    event loop responsive, replacing Node's ``readline/promises``.

    Raises:
        SystemExit: When the user declines to continue.
    """
    print()
    print("WARNING: Running this agent may consume a noticeable number of tokens.")
    print("   If you don't want to run it now, check the demo output first:")
    print(f"   Demo: {DEMO_FILE}")
    print()

    loop = asyncio.get_running_loop()
    answer: str = await loop.run_in_executor(
        None,
        lambda: input("Do you want to continue? (yes/y): "),
    )

    if answer.strip().lower() not in ("yes", "y"):
        print("Aborted.")
        sys.exit(0)


async def main() -> None:
    """Run the Daily Ops Generator."""
    today = date.today().isoformat()

    print()
    print("=" * 44)
    print(f"  Daily Ops Generator — {today}")
    print("=" * 44)
    print()

    await confirm_run()

    task = (
        f"Prepare the Daily Ops note for {today}. "
        f"Start by reading the workflow instructions from workflows/daily-ops.md "
        f"using the read_file tool. "
        f"Then follow the steps described in the workflow precisely. "
        f"Make sure to write the final output to output/{today}.md"
    )

    logger.info("Starting orchestrator agent for %s", today)
    result = await run_agent("orchestrator", task)

    print()
    print("=" * 44)
    print("  Result")
    print("=" * 44)
    print()
    print(result)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
