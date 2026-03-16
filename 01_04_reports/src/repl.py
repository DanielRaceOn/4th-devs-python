# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL for the image editing agent.
Maintains conversation history across turns for multi-turn context.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/repl.js

"""

import asyncio
from typing import Optional

from .agent import run
from .helpers.stats import reset_stats
from .helpers.logger import log
from .mcp.client import McpSession


async def run_repl(
    *,
    mcp_client: Optional[McpSession] = None,
    mcp_tools: Optional[list] = None,
) -> None:
    """Run the interactive REPL loop for the image editing agent.

    Reads user input from stdin, dispatches each query to the agent, and prints
    the response. Maintains conversation history across turns so the model has
    full context of the editing session. Type ``exit`` to quit or ``clear`` to
    reset the conversation.

    Args:
        mcp_client: Connected MCP session for file system access.
        mcp_tools: MCP tool definition objects (from ``list_mcp_tools``).
    """
    history: list = []
    loop = asyncio.get_event_loop()

    while True:
        try:
            # Run blocking stdin read in a thread to keep the event loop free
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except (EOFError, KeyboardInterrupt):
            user_input = "exit"

        if user_input.lower() == "exit":
            break

        if user_input.lower() == "clear":
            history = []
            reset_stats()
            log.success("Conversation cleared\n")
            continue

        if not user_input.strip():
            continue

        try:
            result = await run(
                user_input,
                mcp_client=mcp_client,
                mcp_tools=mcp_tools,
                conversation_history=history,
            )
            history = result["conversation_history"]
            print(f"\nAssistant: {result['response']}\n")
        except Exception as err:
            log.error("Error", str(err))
            print("")
