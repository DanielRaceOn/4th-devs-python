# -*- coding: utf-8 -*-

#   errors.py

"""
### Description:
Error response helpers — standard error dicts and factory functions.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

from typing import Any

OUT_OF_SCOPE_ERROR: dict[str, Any] = {
    "success": False,
    "code": "OUT_OF_SCOPE",
    "error": "Path resolves outside the sandbox root.",
}


def error_response(
    code: str, message: str, hint: str | None = None, **extra: Any
) -> dict[str, Any]:
    """Build a standard error response dict.

    Args:
        code: Short error code string (e.g. ``"NOT_FOUND"``).
        message: Human-readable error description.
        hint: Optional hint to guide the caller.
        **extra: Additional fields merged into the response.

    Returns:
        Dict with ``success=False``, ``code``, ``error``, and optional ``hint``.
    """
    resp: dict[str, Any] = {"success": False, "code": code, "error": message, **extra}
    if hint:
        resp["hint"] = hint
    return resp
