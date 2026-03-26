# -*- coding: utf-8 -*-

#   __init__.py

"""
### Description:
Library helpers for the files-mcp package.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from lib.checksum import checksum_file, checksum_text
from lib.diff import make_diff
from lib.filetypes import is_text_file, matches_glob, matches_type
from lib.ignore import create_ignore_matcher
from lib.lines import add_line_numbers, parse_line_range
from lib.paths import is_sandbox_root, rel, resolve_safe
from lib.search import search_files

__all__ = [
    "checksum_file",
    "checksum_text",
    "make_diff",
    "is_text_file",
    "matches_glob",
    "matches_type",
    "create_ignore_matcher",
    "add_line_numbers",
    "parse_line_range",
    "is_sandbox_root",
    "rel",
    "resolve_safe",
    "search_files",
]
