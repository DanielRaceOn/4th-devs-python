# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for the Video Processing Agent. Prompts the user for confirmation,
connects to the MCP files server, and runs the interactive REPL loop.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `app.js`


"""

import asyncio
import logging
import sys

from src.helpers.logger import log
from src.helpers.shutdown import on_shutdown
from src.helpers.stats import log_stats
from src.mcp.client import create_mcp_client, list_mcp_tools
from src.native.tools import native_tools
from src.repl import run_repl

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

EXAMPLE_QUERY = (
    "List 4 big claims breakdown from this video "
    "https://www.youtube.com/watch?v=Iar4yweKGoI"
)

DEMO_FILE = "01_04_video/workspace/demo/breakdown.md"


async def confirm_run() -> None:
    """Prompt the user for confirmation before consuming tokens.

    Runs the blocking ``input()`` call in an executor to keep the asyncio event
    loop responsive.

    Raises:
        SystemExit: When the user declines.
    """
    print()
    print("⚠️  WARNING: Running this agent may consume a noticeable number of tokens.")
    print("   If you don't want to run it now, check the demo output first:")
    print(f"   Demo: {DEMO_FILE}")
    print()

    answer: str = await asyncio.to_thread(
        input, "Do you want to continue? (yes/y): "
    )

    if answer.strip().lower() not in ("yes", "y"):
        print("Aborted.")
        sys.exit(0)


async def main() -> None:
    """Run the Video Processing Agent."""
    log.box("Video Processing Agent\nType 'exit' to quit, 'clear' to reset")
    await confirm_run()

    log.start("Connecting to MCP server...")

    async with create_mcp_client() as session:
        mcp_tools = await list_mcp_tools(session)
        log.success(f"MCP tools: {', '.join(t.name for t in mcp_tools)}")
        log.info(f"Native tools: {', '.join(t['name'] for t in native_tools)}")
        print(f"\n  Example: {EXAMPLE_QUERY}\n")

        async def _cleanup() -> None:
            log_stats()

        # Register shutdown handler — logs stats on Ctrl-C / SIGTERM
        on_shutdown(_cleanup)

        try:
            await run_repl(session=session, mcp_tools=mcp_tools)
        finally:
            log_stats()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except Exception as exc:
        log.error("Fatal error", str(exc))
        sys.exit(1)
