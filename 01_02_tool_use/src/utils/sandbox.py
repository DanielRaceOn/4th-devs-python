# -*- coding: utf-8 -*-

#   sandbox.py

"""
### Description:
Sandbox filesystem utilities: initialise a clean sandbox directory before each
run, and resolve relative paths while enforcing a strict boundary — any attempt
to access a path outside the sandbox raises an error.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/utils/sandbox.js`


"""

import shutil
from pathlib import Path

from ..config import SANDBOX_ROOT


async def initialize_sandbox() -> None:
    """Wipe and re-create the sandbox directory so each run starts clean.

    Mirrors ``initializeSandbox()`` in sandbox.js — removes the entire tree
    (if it exists) then creates a fresh empty directory.
    """
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.mkdir(parents=True)


def resolve_sandbox_path(relative_path: str) -> Path:
    """Resolve *relative_path* inside the sandbox, blocking path traversal.

    Args:
        relative_path: A path relative to the sandbox root (e.g. ``"docs/notes.txt"``).

    Returns:
        Absolute :class:`~pathlib.Path` inside the sandbox.

    Raises:
        PermissionError: If the resolved path escapes the sandbox boundary.
    """
    resolved = (SANDBOX_ROOT / relative_path).resolve()

    # Ensure the resolved path is still inside the sandbox.
    try:
        resolved.relative_to(SANDBOX_ROOT.resolve())
    except ValueError:
        raise PermissionError(
            f'Access denied: path "{relative_path}" is outside sandbox'
        )

    return resolved
