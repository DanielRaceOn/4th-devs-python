# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
MCP Translator Agent — connects to files-mcp, starts a file-watching
translation loop, and exposes HTTP endpoints for on-demand translation.

Run:
    python app.py

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `app.js`

"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import server as server_config
from src.helpers.logger import log
from src.mcp.client import create_mcp_client, list_mcp_tools
from src.server import start_http_server
from src.translator import run_translation_loop

# Shared state for the HTTP server to access
_mcp_client = None
_mcp_tools: list = []


async def main() -> None:
    global _mcp_client, _mcp_tools

    log.box("MCP Translator Agent\nAccurate translations to English with tone, formatting & nuances")

    # Connect to files-mcp (stdio transport, config in mcp.json)
    log.start("Connecting to MCP server...")
    _mcp_client = await create_mcp_client()
    _mcp_tools = await list_mcp_tools(_mcp_client)
    log.success(
        f"Connected with {len(_mcp_tools)} tools: {', '.join(t.name for t in _mcp_tools)}"
    )

    # HTTP API for on-demand translation (runs in background thread)
    http_server = start_http_server(
        server_config,
        lambda: {"mcp_client": _mcp_client, "mcp_tools": _mcp_tools},
    )

    # Handle shutdown signals
    loop = asyncio.get_running_loop()

    async def shutdown():
        log.warn("Shutting down...")
        if _mcp_client:
            await _mcp_client.__aexit__(None, None, None)
        http_server.shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    # Watch workspace/translate/ for new files (runs until shutdown)
    await run_translation_loop(_mcp_client, _mcp_tools)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as error:
        log.error("Startup error", str(error))
        sys.exit(1)
