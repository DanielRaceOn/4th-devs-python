# -*- coding: utf-8 -*-

#   fs_manage.py

"""
### Description:
fs_manage MCP tool — structural filesystem operations within the sandbox.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from typing import Optional

from lib.paths import is_sandbox_root, resolve_safe
from utils.errors import OUT_OF_SCOPE_ERROR, error_response


def _iso(ts: float) -> str:
    """Convert a POSIX timestamp to an ISO 8601 UTC string.

    Args:
        ts: POSIX timestamp (seconds since epoch).

    Returns:
        ISO 8601 string ending with ``Z``.
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def fs_manage(
    operation: str,
    path: str,
    target: Optional[str] = None,
    recursive: bool = False,
    force: bool = False,
) -> str:
    """Perform structural filesystem operations within the sandbox.

    Args:
        operation: ``"delete"`` | ``"rename"`` | ``"move"`` | ``"copy"``
            | ``"mkdir"`` | ``"stat"``.
        path: Source path within sandbox.
        target: Destination path for rename/move/copy.
        recursive: Create parent dirs (mkdir), include subdirs (copy), or
            delete non-empty directories (delete).
        force: Overwrite if target exists.

    Returns:
        JSON-encoded result dict.
    """
    resolved = resolve_safe(path)
    if resolved is None:
        return json.dumps({**OUT_OF_SCOPE_ERROR, "operation": operation, "path": path})

    # --- stat ---
    if operation == "stat":
        if not resolved.exists():
            return json.dumps(error_response(
                "NOT_FOUND", f"Path not found: {path}", operation=operation, path=path
            ))
        stat = resolved.stat()
        return json.dumps({
            "success": True,
            "operation": operation,
            "path": path,
            "stat": {
                "kind": "directory" if resolved.is_dir() else "file",
                "isDirectory": resolved.is_dir(),
                "size": stat.st_size,
                "modified": _iso(stat.st_mtime),
                "created": _iso(stat.st_ctime),
            },
        })

    # --- mkdir ---
    if operation == "mkdir":
        resolved.mkdir(parents=recursive, exist_ok=True)
        return json.dumps({"success": True, "operation": operation, "path": path})

    # --- delete ---
    if operation == "delete":
        if not resolved.exists():
            return json.dumps(error_response(
                "NOT_FOUND", f"Path not found: {path}", operation=operation, path=path
            ))
        if is_sandbox_root(resolved):
            return json.dumps(error_response(
                "FORBIDDEN", "Cannot delete the sandbox root.", operation=operation, path=path
            ))
        if resolved.is_dir():
            if recursive:
                shutil.rmtree(resolved)
            elif any(resolved.iterdir()):
                return json.dumps(error_response(
                    "NOT_EMPTY",
                    "Directory is not empty. Only empty directories can be deleted.",
                    hint="Delete files inside first, or use recursive=true.",
                    operation=operation,
                    path=path,
                ))
            else:
                resolved.rmdir()
        else:
            resolved.unlink()
        return json.dumps({"success": True, "operation": operation, "path": path})

    # --- rename / move / copy — require target ---
    if target is None:
        return json.dumps(error_response(
            "MISSING_TARGET",
            f"'target' required for operation '{operation}'",
            operation=operation,
            path=path,
        ))

    resolved_target = resolve_safe(target)
    if resolved_target is None:
        return json.dumps({**OUT_OF_SCOPE_ERROR, "operation": operation, "path": path})

    if not resolved.exists():
        return json.dumps(error_response(
            "NOT_FOUND", f"Source not found: {path}", operation=operation, path=path
        ))

    if operation in ("rename", "move"):
        if resolved_target.exists() and not force:
            return json.dumps(error_response(
                "ALREADY_EXISTS",
                f"Target already exists: {target}. Use force=true to overwrite.",
                operation=operation,
                path=path,
            ))
        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(resolved, resolved_target)
        return json.dumps({"success": True, "operation": operation, "path": path, "target": target})

    if operation == "copy":
        if resolved_target.exists() and not force:
            return json.dumps(error_response(
                "ALREADY_EXISTS",
                f"Target already exists: {target}. Use force=true to overwrite.",
                operation=operation,
                path=path,
            ))
        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        if resolved.is_dir():
            if recursive:
                shutil.copytree(resolved, resolved_target, dirs_exist_ok=force)
            else:
                return json.dumps(error_response(
                    "IS_DIRECTORY",
                    "Source is a directory. Use recursive=true to copy directories.",
                    operation=operation,
                    path=path,
                ))
        else:
            shutil.copy2(resolved, resolved_target)
        return json.dumps({"success": True, "operation": operation, "path": path, "target": target})

    return json.dumps(error_response(
        "UNKNOWN_OPERATION", f"Unknown operation: {operation}", operation=operation, path=path
    ))
