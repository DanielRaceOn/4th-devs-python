# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Image Editing Agent — interactive terminal REPL that combines MCP file tools
with native image generation/editing (Gemini or OpenRouter) and quality analysis.

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
    "Restyle workspace/input/SCR-20260131-ugqp.jpeg to match workspace/style-guide.md",
    "Create a monochrome concept sketch of a futuristic motorcycle",
    "Edit workspace/input/SCR-20260131-ugqp.jpeg into a black-and-white pencil sketch",
    "Review the latest generated image for blocking issues and style consistency",
]

DEMO_FILES = [
    "workspace/demo/SCR_DEMO_input.jpeg",
    "workspace/demo/SCR_DEMO_output.jpg",
]


def _confirm_run() -> None:
    """Prompt the user to confirm before starting (may incur API costs)."""
    print(
        "\n⚠️  UWAGA: Uruchomienie tego agenta może zużyć zauważalną liczbę tokenów i wygenerować obrazy."
    )
    print("   Jeśli nie chcesz uruchamiać go teraz, najpierw sprawdź pliki demo:")
    print(f"   Demo input : {DEMO_FILES[0]}")
    print(f"   Demo output: {DEMO_FILES[1]}")
    print("")

    answer = input("Czy chcesz kontynuować? (yes/y): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Przerwano.")
        sys.exit(0)


def _print_tools() -> None:
    log.heading("TOOLS")
    for tool in native_tools:
        name = tool["name"].ljust(14)
        desc = tool["description"].split(".")[0]
        log.info(f"{name} — {desc}")


def _print_examples() -> None:
    log.heading("EXAMPLES", "For demo purposes, try these queries:")
    for example in EXAMPLES:
        log.example(example)
    log.hint("Type 'exit' to quit, 'clear' to reset conversation")


async def main() -> None:
    log.box("Image Editing Agent")
    _confirm_run()
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
