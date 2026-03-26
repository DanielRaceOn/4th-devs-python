# -*- coding: utf-8 -*-

#   filetypes.py

"""
### Description:
File type detection — text/binary heuristics, extension matching, glob filtering.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Map of logical type names to file extensions (subset of common types).
_TYPE_EXTENSIONS: dict[str, list[str]] = {
    "py": [".py"],
    "js": [".js", ".mjs", ".cjs"],
    "ts": [".ts", ".mts", ".cts"],
    "jsx": [".jsx"],
    "tsx": [".tsx"],
    "json": [".json", ".jsonc"],
    "yaml": [".yaml", ".yml"],
    "toml": [".toml"],
    "md": [".md", ".mdx"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
    "sh": [".sh", ".bash", ".zsh"],
    "txt": [".txt"],
    "xml": [".xml"],
    "csv": [".csv"],
    "sql": [".sql"],
    "go": [".go"],
    "rs": [".rs"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
    "rb": [".rb"],
    "php": [".php"],
}


def is_text_file(path: Path) -> bool:
    """Heuristic check whether a file appears to be text (not binary).

    Reads the first 4 KB and checks for null bytes.

    Args:
        path: Absolute file path.

    Returns:
        ``True`` if the file appears to be text.
    """
    try:
        chunk = path.read_bytes()[:4096]
        return b"\x00" not in chunk
    except OSError:
        return False


def matches_type(path: Path, types: list[str]) -> bool:
    """Return True if the file's extension matches any of the given type names.

    Args:
        path: File path to check.
        types: List of logical type names (e.g. ``["py", "js"]``).

    Returns:
        ``True`` if the file matches at least one type.
    """
    ext = path.suffix.lower()
    for t in types:
        allowed = _TYPE_EXTENSIONS.get(t, [f".{t}"])
        if ext in allowed:
            return True
    return False


def matches_glob(path: Path, patterns: list[str]) -> bool:
    """Return True if the file name or path matches any of the given glob patterns.

    Args:
        path: File path to check.
        patterns: List of glob patterns (e.g. ``["*.py", "src/**"]``).

    Returns:
        ``True`` if at least one pattern matches.
    """
    name = path.name
    posix = path.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(posix, pattern):
            return True
    return False
