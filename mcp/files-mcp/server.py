# -*- coding: utf-8 -*-

#   server.py

"""
### Description:
FastMCP instance, tool registration, and entry point for the files-mcp server.

Run:
    python server.py

Environment:
    FS_ROOT     - Absolute or relative path to the sandbox root directory
    LOG_LEVEL   - Logging level: debug | info | warning | error (default: info)

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

import sys
from pathlib import Path

# Add this directory to sys.path so all submodules can use direct imports.
# Required because MCP clients invoke this script directly (not as a package).
_pkg = Path(__file__).parent
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from tools import fs_manage, fs_read, fs_search, fs_write  # noqa: E402

mcp = FastMCP("files-mcp")

mcp.tool()(fs_read)
mcp.tool()(fs_write)
mcp.tool()(fs_search)
mcp.tool()(fs_manage)

if __name__ == "__main__":
    from config import log  # noqa: E402

    log.info("Starting files-mcp server (stdio transport)")
    mcp.run(transport="stdio")
