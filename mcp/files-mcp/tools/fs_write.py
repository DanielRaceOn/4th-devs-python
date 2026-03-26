# -*- coding: utf-8 -*-

#   fs_write.py

"""
### Description:
fs_write MCP tool — create or update files within the sandbox.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import json
from typing import Optional

from lib.checksum import checksum_file, checksum_text
from lib.diff import make_diff
from lib.lines import parse_line_range
from lib.paths import resolve_safe
from utils.errors import OUT_OF_SCOPE_ERROR


def fs_write(
    path: str,
    operation: str,
    content: Optional[str] = None,
    action: Optional[str] = None,
    lines: Optional[str] = None,
    checksum: Optional[str] = None,
    dryRun: bool = False,
    createDirs: bool = True,
) -> str:
    """Create or update files within the sandbox.

    Args:
        path: Relative path within sandbox.
        operation: ``"create"`` or ``"update"``.
        content: Text content to write.
        action: Required for update: ``"replace"`` | ``"insert_before"``
            | ``"insert_after"`` | ``"delete_lines"``.
        lines: Target line range, e.g. ``"10"`` or ``"10-15"``.
        checksum: If given, verify file hasn't changed since last read.
        dryRun: Preview diff without writing.
        createDirs: Create parent directories automatically (default: True).

    Returns:
        JSON-encoded result dict.
    """
    resolved = resolve_safe(path)
    if resolved is None:
        return json.dumps(OUT_OF_SCOPE_ERROR)

    if createDirs:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    if operation == "create":
        if content is None:
            return json.dumps({"status": "error", "error": "'content' required for create"})
        if resolved.exists():
            return json.dumps({
                "status": "error",
                "code": "ALREADY_EXISTS",
                "error": f"File already exists: {path}. Use operation='update' to modify it.",
            })
        # Ensure POSIX trailing newline
        text_to_write = content if content.endswith("\n") else content + "\n"
        new_lines = text_to_write.splitlines()
        diff = make_diff([], new_lines)
        if not dryRun:
            resolved.write_text(text_to_write, encoding="utf-8")
        new_cksum = checksum_file(resolved) if not dryRun else checksum_text(text_to_write)
        return json.dumps({
            "status": "preview" if dryRun else "applied",
            "path": path,
            "operation": operation,
            "result": {"action": "create", "newChecksum": new_cksum, "diff": diff},
        })

    if operation == "update":
        if not resolved.exists():
            return json.dumps({"status": "error", "error": f"File not found: {path}"})
        if not resolved.is_file():
            return json.dumps({"status": "error", "error": f"Not a file: {path}"})

        if checksum and checksum_file(resolved) != checksum:
            return json.dumps({
                "status": "error",
                "error": "Checksum mismatch — file has changed since last read.",
                "hint": "Re-read the file with fs_read to get the current checksum.",
            })

        if action is None:
            return json.dumps({"status": "error", "error": "'action' required for update"})
        if lines is None and action != "delete_lines":
            return json.dumps({"status": "error", "error": "'lines' required for update"})

        original_text = resolved.read_text(encoding="utf-8")
        had_trailing_newline = original_text.endswith("\n")
        original_lines = original_text.splitlines()
        total = len(original_lines)
        new_lines = list(original_lines)

        if action == "delete_lines":
            if lines is None:
                return json.dumps({"status": "error", "error": "'lines' required for delete_lines"})
            result = parse_line_range(lines, total)
            if isinstance(result, str):
                return json.dumps({"status": "error", "error": result})
            start, end = result
            del new_lines[start : end + 1]
        else:
            result = parse_line_range(lines, total)  # type: ignore[arg-type]
            if isinstance(result, str):
                return json.dumps({"status": "error", "error": result})
            start, end = result
            incoming = content.splitlines() if content else []
            if action == "replace":
                new_lines[start : end + 1] = incoming
            elif action == "insert_before":
                new_lines[start:start] = incoming
            elif action == "insert_after":
                new_lines[end + 1 : end + 1] = incoming
            else:
                return json.dumps({"status": "error", "error": f"Unknown action: {action}"})

        new_text = "\n".join(new_lines)
        # Preserve trailing newline that was present in the original file (B1 fix)
        if had_trailing_newline and not new_text.endswith("\n"):
            new_text += "\n"

        diff = make_diff(original_lines, new_lines)
        if not dryRun:
            resolved.write_text(new_text, encoding="utf-8")
        new_cksum = checksum_file(resolved) if not dryRun else checksum_text(new_text)
        return json.dumps({
            "status": "preview" if dryRun else "applied",
            "path": path,
            "operation": operation,
            "result": {"action": action, "newChecksum": new_cksum, "diff": diff},
        })

    return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})
