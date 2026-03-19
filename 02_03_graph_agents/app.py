# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Graph RAG Agent entry point. Connects to Neo4j, ensures the graph schema,
indexes the workspace, then starts an interactive REPL where the user can
ask questions answered via hybrid retrieval and graph exploration.

Commands available in the REPL:
  exit             — quit the agent
  clear            — reset conversation history and token stats
  reindex          — re-scan and re-index workspace/
  reindex --force  — wipe entire graph then re-index workspace/

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `app.js`

"""

import asyncio
import os
import sys

# Ensure UTF-8 output on Windows (cp1252 terminal can't encode emoji/special chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.graph.driver import create_driver, verify_connection
from src.graph.schema import ensure_schema
from src.graph.indexer import index_workspace
from src.agent.tools import create_tools
from src.helpers.shutdown import on_shutdown
from src.helpers.stats import log_stats
from src.helpers.logger import log
from src.repl import run_repl


async def main() -> None:
    """Start the Graph RAG Agent."""
    log.box("Graph RAG Agent\nCommands: 'exit' | 'clear' | 'reindex' | 'reindex --force'")

    # 1. Connect to Neo4j
    log.start("Connecting to Neo4j...")
    driver = create_driver(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        username=os.environ.get("NEO4J_USERNAME", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "password"),
    )
    await verify_connection(driver)
    log.success("Neo4j connected")

    # 2. Ensure schema (constraints + indexes)
    log.start("Ensuring graph schema...")
    await ensure_schema(driver)

    # 3. Index workspace files
    log.start("Indexing workspace...")
    await index_workspace(driver, "workspace")
    log.success("Indexing complete")

    # 4. Create agent tools
    tools = create_tools(driver)

    # 5. Register graceful shutdown handler
    async def _cleanup() -> None:
        log_stats()
        await driver.close()

    shutdown = on_shutdown(_cleanup)

    # 6. Run interactive REPL
    await run_repl(tools=tools, driver=driver)

    # Normal exit path (user typed 'exit')
    await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        log.error("Startup error", str(err))
        sys.exit(1)
