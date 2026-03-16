# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL for the video generation agent.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/repl.js

"""

import aioconsole

from .agent import run
from .helpers.stats import reset_stats
from .helpers.logger import log


async def run_repl(mcp_client, mcp_tools) -> None:
    """Run the interactive REPL loop.

    Args:
        mcp_client: Connected MCP client
        mcp_tools: List of available MCP tools
    """
    history = []

    while True:
        try:
            user_input = await aioconsole.ainput("You: ")
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
            history = result["conversationHistory"]
            print(f"\nAssistant: {result['response']}\n")
        except Exception as err:
            log.error("Error", str(err))
            print("")
