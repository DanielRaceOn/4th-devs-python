# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Configuration — env vars, FS_ROOT resolution, logging setup, constants.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

_raw_level = os.environ.get("LOG_LEVEL", "info").lower()
logging.basicConfig(
    level=_LOG_LEVEL_MAP.get(_raw_level, logging.INFO),
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("files-mcp")

# ---------------------------------------------------------------------------
# Sandbox root
# ---------------------------------------------------------------------------

# Path.resolve() handles both absolute and relative paths — the is_absolute()
# branch in the original was redundant.
FS_ROOT: Path = Path(os.environ.get("FS_ROOT", "./workspace")).resolve()
FS_ROOT.mkdir(parents=True, exist_ok=True)
log.info(f"Sandbox root: {FS_ROOT}")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FS_READ_MAX_LINES: int = 100
