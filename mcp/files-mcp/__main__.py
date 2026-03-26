# -*- coding: utf-8 -*-

#   __main__.py

"""
### Description:
Entry point — run the files-mcp server over stdio transport.

Usage:
    python -m mcp.files-mcp

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from .config import log
from .server import mcp

if __name__ == "__main__":
    log.info("Starting files-mcp server (stdio transport)")
    mcp.run(transport="stdio")
