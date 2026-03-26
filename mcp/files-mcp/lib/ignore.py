# -*- coding: utf-8 -*-

#   ignore.py

"""
### Description:
.gitignore pattern support — creates a matcher callable from .gitignore files found
in the given directory (and its parents up to FS_ROOT).

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Callable

from config import FS_ROOT

try:
    import pathspec  # type: ignore[import]

    _HAS_PATHSPEC = True
except ImportError:
    _HAS_PATHSPEC = False


def _load_patterns(directory: Path) -> list[str]:
    """Collect .gitignore patterns from directory up to FS_ROOT.

    Args:
        directory: Starting directory.

    Returns:
        List of raw gitignore pattern strings.
    """
    patterns: list[str] = []
    current = directory
    while True:
        gi = current / ".gitignore"
        if gi.is_file():
            for line in gi.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        if current == FS_ROOT or current.parent == current:
            break
        current = current.parent
    return patterns


def create_ignore_matcher(directory: Path) -> Callable[[Path], bool]:
    """Build a matcher that returns True for paths that should be ignored.

    Uses the ``pathspec`` library (gitignore semantics) when available, otherwise
    falls back to simple fnmatch glob matching.

    Args:
        directory: Root directory to search for .gitignore files.

    Returns:
        Callable that accepts an absolute ``Path`` and returns ``True`` if it
        should be ignored.
    """
    patterns = _load_patterns(directory)

    if not patterns:
        return lambda _: False

    if _HAS_PATHSPEC:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

        def _match_pathspec(path: Path) -> bool:
            try:
                rel = path.relative_to(directory).as_posix()
            except ValueError:
                return False
            return spec.match_file(rel)

        return _match_pathspec

    # Fallback: simple fnmatch on filename and partial path
    def _match_fnmatch(path: Path) -> bool:
        name = path.name
        try:
            rel = path.relative_to(directory).as_posix()
        except ValueError:
            rel = name
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                return True
        return False

    return _match_fnmatch
