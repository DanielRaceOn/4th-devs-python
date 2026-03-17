# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL for the hybrid RAG agent. Supports 'exit', 'clear' (reset
conversation and stats), and 'reindex' (re-scan workspace) commands.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/repl.js

"""

import asyncio
import sqlite3
from typing import Any, Dict

from .agent.index import run, create_conversation
from .db.indexer import index_workspace
from .helpers.stats import reset_stats
from .helpers import logger as log


async def run_repl(
    tools: Dict[str, Any],
    conn: sqlite3.Connection,
    workspace: str = "workspace",
) -> None:
    """Run the interactive REPL loop.

    Commands:
    - ``exit`` — quit the REPL
    - ``clear`` — reset conversation history and token stats
    - ``reindex`` — re-scan and re-index the workspace directory

    Args:
        tools: Tool interface dict from :func:`~src.agent.tools.create_tools`.
        conn: Open database connection.
        workspace: Path to the workspace directory for the ``reindex`` command.
    """
    conversation = create_conversation()
    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input: str = await loop.run_in_executor(
                None, lambda: input("You: ")
            )
        except (EOFError, KeyboardInterrupt):
            break

        cmd = user_input.strip().lower()

        if cmd == "exit":
            break

        if cmd == "clear":
            conversation = create_conversation()
            reset_stats()
            log.success("Conversation cleared\n")
            continue

        if cmd == "reindex":
            log.start("Re-indexing workspace...")
            await index_workspace(conn, workspace)
            log.success("Re-indexing complete\n")
            continue

        if not user_input.strip():
            continue

        try:
            response_text, new_history = await run(
                user_input,
                tools=tools,
                conversation_history=conversation["history"],
            )
            conversation["history"] = new_history
            print(f"\nAssistant: {response_text}\n")
        except Exception as exc:  # noqa: BLE001
            log.error("Error", str(exc))
            print()
