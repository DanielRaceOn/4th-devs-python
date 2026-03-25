# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL loop for the video processing agent. Reads user input,
dispatches to the agent, and prints the response. Supports ``exit`` to quit and
``clear`` to reset conversation history and stats.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/repl.js`


"""

import asyncio
import logging
from typing import Any

from mcp import ClientSession

from .agent import create_conversation, run
from .helpers.logger import log
from .helpers.stats import reset_stats

logger = logging.getLogger(__name__)


async def run_repl(
    *,
    session: ClientSession,
    mcp_tools: list[Any],
) -> None:
    """Run the interactive REPL loop.

    Reads input from stdin in a background thread (via ``asyncio.to_thread``) so
    the asyncio event loop stays responsive while waiting for the user to type.

    Special commands:
    - ``exit`` — break the loop and return.
    - ``clear`` — reset conversation history and usage stats.
    - Empty input — skipped silently.

    Args:
        session: Active MCP client session (passed through to the agent).
        mcp_tools: MCP Tool objects (passed through to the agent).
    """
    conversation = create_conversation()

    while True:
        try:
            # Run blocking input() in a thread pool to avoid blocking the event loop
            user_input: str = await asyncio.to_thread(input, "You: ")
        except EOFError:
            # stdin closed (e.g. piped input finished)
            break

        if user_input.lower() == "exit":
            break

        if user_input.lower() == "clear":
            conversation = create_conversation()
            reset_stats()
            log.success("Conversation cleared\n")
            continue

        if not user_input.strip():
            continue

        try:
            result = await run(
                user_input,
                session=session,
                mcp_tools=mcp_tools,
                conversation_history=conversation["history"],
            )
            conversation["history"] = result["conversation_history"]
            print(f"\nAssistant: {result['response']}\n")
        except Exception as exc:
            log.error("Error", str(exc))
            print("")
