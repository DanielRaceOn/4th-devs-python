# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Hybrid RAG Agent entry point. Initializes the SQLite database with FTS5 and
sqlite-vec, indexes workspace documents, and runs an interactive REPL where
the user can ask questions answered by hybrid document retrieval.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      app.js

"""

import asyncio
import sys
from pathlib import Path

# Resolve workspace path relative to this file so the script can be run
# from any working directory (e.g. project root with .venv/Scripts/python).
_MODULE_DIR = Path(__file__).parent
_WORKSPACE = str(_MODULE_DIR / "workspace")
_DB_PATH = str(_MODULE_DIR / ".." / ".data" / "hybrid.db")

from src.db.index import init_db
from src.db.indexer import index_workspace
from src.agent.tools import create_tools
from src.repl import run_repl
from src.helpers.stats import log_stats
from src.helpers import logger as log


async def main() -> None:
    """Initialize the database, index the workspace, and start the REPL."""
    log.box("Hybrid RAG Agent\nCommands: 'exit' | 'clear' | 'reindex'")

    # 1. Database
    log.start("Initializing database...")
    conn = init_db(_DB_PATH)
    log.success("Database ready")

    # 2. Index workspace documents
    log.start("Indexing workspace...")
    await index_workspace(conn, _WORKSPACE)
    log.success("Indexing complete")

    # 3. Create tools
    tools = create_tools(conn)

    try:
        await run_repl(tools=tools, conn=conn, workspace=_WORKSPACE)
    finally:
        log_stats()
        conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        log.error("Startup error", str(err))
        sys.exit(1)
