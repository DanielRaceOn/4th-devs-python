# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Video Generation Agent — interactive terminal REPL for generating videos from text prompts
or image frames using Kling AI (via Replicate) and Gemini for frame generation.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      app.js

"""

import asyncio
import sys

from src.mcp.client import create_mcp_client, list_mcp_tools
from src.native.tools import native_tools
from src.repl import run_repl
from src.helpers.shutdown import on_shutdown
from src.helpers.stats import log_stats
from src.helpers.logger import log

EXAMPLES = [
    "Create a 10-second video of a red fox jumping over a fence into snow",
    "Generate start and end frames for a butterfly emerging from a cocoon, then animate",
    "Make a video of a cat walking through autumn leaves",
    "Create frames using the template.json style, then generate a 5-second clip",
]


def _print_tools() -> None:
    log.heading("TOOLS")
    for tool in native_tools:
        name = tool["name"].ljust(16)
        desc = tool["description"].split(".")[0]
        log.info(f"{name} — {desc}")


def _print_examples() -> None:
    log.heading("EXAMPLES", "For demo purposes, try these queries:")
    for example in EXAMPLES:
        log.example(example)
    log.hint("Type 'exit' to quit, 'clear' to reset conversation")


async def main() -> None:
    log.box("Video Generation Agent\nType 'exit' to quit, 'clear' to reset")
    _print_tools()

    mcp_client = None

    try:
        log.start("Connecting to MCP server...")
        mcp_client = await create_mcp_client()
        mcp_tools = await list_mcp_tools(mcp_client)
        log.success(f"MCP: {', '.join(t.name for t in mcp_tools)}")

        _print_examples()

        async def cleanup() -> None:
            log_stats()
            if mcp_client:
                await mcp_client.close()

        shutdown = on_shutdown(cleanup)

        await run_repl(mcp_client=mcp_client, mcp_tools=mcp_tools)
        await shutdown()

    except Exception as error:
        if mcp_client:
            try:
                await mcp_client.close()
            except Exception:
                pass
        raise error


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        log.error("Startup error", str(err))
        sys.exit(1)
