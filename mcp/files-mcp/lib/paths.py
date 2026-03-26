# -*- coding: utf-8 -*-

#   paths.py

"""
### Description:
Sandbox path resolution — safe path containment checks within FS_ROOT.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

from pathlib import Path

from config import FS_ROOT


def resolve_safe(relative: str) -> Path | None:
    """Resolve a relative path inside FS_ROOT.

    Args:
        relative: A relative path string provided by the caller (``"."`` = root).

    Returns:
        Resolved absolute ``Path`` if inside sandbox, else ``None``.
    """
    if relative in ("", "."):
        return FS_ROOT
    candidate = (FS_ROOT / relative).resolve()
    try:
        candidate.relative_to(FS_ROOT)
        return candidate
    except ValueError:
        return None


def rel(path: Path) -> str:
    """Return path relative to FS_ROOT as a POSIX string.

    Args:
        path: Absolute path inside sandbox.

    Returns:
        POSIX-style relative path string.
    """
    return path.relative_to(FS_ROOT).as_posix()


def is_sandbox_root(path: Path) -> bool:
    """Return True if path is exactly FS_ROOT.

    Args:
        path: Absolute resolved path.

    Returns:
        ``True`` when path equals the sandbox root.
    """
    return path == FS_ROOT
