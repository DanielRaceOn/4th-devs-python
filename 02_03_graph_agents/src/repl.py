# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL for the graph RAG agent. Reads user input from stdin,
handles built-in commands (exit, clear, reindex), and routes all other
input to the agent loop.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/repl.js`

"""

import asyncio

from neo4j import AsyncDriver

from .agent.index import run, create_conversation
from .graph.indexer import index_workspace, clear_graph
from .helpers.stats import reset_stats
from .helpers.logger import log


async def run_repl(*, tools: dict, driver: AsyncDriver) -> None:
    """Start the interactive REPL loop.

    Built-in commands:
    - ``exit``             — break the loop and return
    - ``clear``            — reset conversation history and token stats
    - ``reindex``          — re-scan and re-index workspace/
    - ``reindex --force``  — wipe entire graph, then re-index workspace/

    Any other non-empty input is forwarded to the agent.

    Args:
        tools: Tool registry from ``create_tools()``.
        driver: Neo4j async driver (needed for reindex commands).
    """
    conversation = create_conversation()
    loop = asyncio.get_event_loop()

    while True:
        try:
            # Use run_in_executor so we don't block the event loop during input
            user_input: str = await loop.run_in_executor(None, input, "You: ")
        except (EOFError, KeyboardInterrupt):
            break

        stripped = user_input.strip()
        lower = stripped.lower()

        if lower == "exit":
            break

        if lower == "clear":
            conversation = create_conversation()
            reset_stats()
            log.success("Conversation cleared\n")
            continue

        if lower.startswith("reindex"):
            force = "--force" in lower
            if force:
                log.start("Clearing graph...")
                await clear_graph(driver)
            log.start("Re-indexing workspace...")
            await index_workspace(driver, "workspace")
            log.success("Re-indexing complete\n")
            continue

        if not stripped:
            continue

        try:
            result = await run(
                stripped,
                tools=tools,
                conversation_history=conversation["history"],
            )
            conversation["history"] = result["conversation_history"]
            print(f"\nAssistant: {result['response']}\n")
        except Exception as err:
            log.error("Error", str(err))
            print()
