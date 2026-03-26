# -*- coding: utf-8 -*-

#   fs_read.py

"""
### Description:
fs_read MCP tool — read files or list directories within the sandbox.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from config import FS_READ_MAX_LINES
from lib.checksum import checksum_file
from lib.filetypes import matches_glob, matches_type
from lib.ignore import create_ignore_matcher
from lib.lines import add_line_numbers, parse_line_range
from lib.paths import rel, resolve_safe
from utils.errors import OUT_OF_SCOPE_ERROR


def _read_file_content(path: Path, lines_spec: Optional[str]) -> dict[str, Any] | str:
    """Read file content and return a content response dict.

    Args:
        path: Absolute file path inside sandbox.
        lines_spec: Optional line range string (e.g. ``"10"`` or ``"10-50"``).

    Returns:
        Dict with keys ``text``, ``checksum``, ``totalLines``, ``truncated``,
        or an error string if ``lines_spec`` is invalid.
    """
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    all_lines = raw_text.splitlines()
    total = len(all_lines)
    cksum = checksum_file(path)
    truncated = False

    if lines_spec:
        result = parse_line_range(lines_spec, total)
        if isinstance(result, str):
            return result  # error message
        start, end = result
        selected = all_lines[start : end + 1]
        numbered = add_line_numbers(selected, offset=start)
    elif total > FS_READ_MAX_LINES:
        selected = all_lines[:FS_READ_MAX_LINES]
        numbered = add_line_numbers(selected)
        truncated = True
    else:
        numbered = add_line_numbers(all_lines)

    return {
        "text": numbered,
        "checksum": cksum,
        "totalLines": total,
        "truncated": truncated,
    }


def _entry_dict(
    p: Path, details: bool, children_count: Optional[int] = None
) -> dict[str, Any]:
    """Build an entry dict for a filesystem item.

    Args:
        p: Absolute path to item.
        details: Whether to include size/modified fields.
        children_count: Number of direct children (directories only).

    Returns:
        Dict with ``path``, ``kind``, and optionally ``children``, ``size``,
        ``modified`` fields.
    """
    entry: dict[str, Any] = {
        "path": rel(p),
        "kind": "directory" if p.is_dir() else "file",
    }
    if children_count is not None:
        entry["children"] = children_count
    if details:
        stat = p.stat()
        entry["size"] = stat.st_size
        entry["modified"] = stat.st_mtime
    return entry


def _collect_entries(
    path: Path,
    depth: int,
    details: bool,
    mode: str,
    types: Optional[list[str]],
    glob_patterns: Optional[list[str]],
    exclude: Optional[list[str]],
    is_ignored: Any,
) -> list[dict[str, Any]]:
    """Recursively collect directory entries, returning a list.

    Args:
        path: Current directory to scan.
        depth: Remaining recursion depth.
        details: Include size/modified.
        mode: ``"tree"`` for dirs only, ``"list"`` / ``"directory"`` for everything.
        types: Optional list of type names to filter files.
        glob_patterns: Optional glob patterns to include.
        exclude: Optional glob patterns to exclude.
        is_ignored: Callable(path) -> bool for .gitignore filtering.

    Returns:
        List of entry dicts.
    """
    if depth < 1:
        return []
    try:
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return []

    entries: list[dict[str, Any]] = []
    for child in children:
        if is_ignored(child):
            continue
        if exclude and matches_glob(child, exclude):
            continue

        if child.is_dir():
            child_count = sum(1 for _ in child.iterdir()) if depth > 1 else None
            entries.append(_entry_dict(child, details, child_count))
            entries.extend(
                _collect_entries(child, depth - 1, details, mode, types, glob_patterns, exclude, is_ignored)
            )
        elif mode != "tree":
            if types and not matches_type(child, types):
                continue
            if glob_patterns and not matches_glob(child, glob_patterns):
                continue
            entries.append(_entry_dict(child, details))

    return entries


def fs_read(
    path: str,
    mode: str = "auto",
    limit: int = 100,
    offset: int = 0,
    lines: Optional[str] = None,
    depth: int = 1,
    details: bool = False,
    types: Optional[list[str]] = None,
    glob: Optional[str] = None,
    exclude: Optional[list[str]] = None,
    respectIgnore: bool = False,
) -> str:
    """Read files or list directories within the sandbox.

    Args:
        path: Relative path within sandbox. ``"."`` means the root.
        mode: ``"auto"`` | ``"tree"`` | ``"list"`` | ``"content"``.
        limit: Max directory entries to return.
        offset: Skip first N directory entries.
        lines: Line range to read, e.g. ``"10"`` or ``"10-50"``.
        depth: Recursion depth for directory listing.
        details: Include size/modified in directory entries.
        types: Filter files by type (e.g. ``["py", "js"]``).
        glob: Glob pattern to include (e.g. ``"*.py"``).
        exclude: Glob patterns to exclude.
        respectIgnore: Skip files matched by .gitignore.

    Returns:
        JSON-encoded result dict.
    """
    resolved = resolve_safe(path)
    if resolved is None:
        return json.dumps(OUT_OF_SCOPE_ERROR)

    effective_mode = mode
    if mode == "auto":
        effective_mode = "directory" if resolved.is_dir() else "content"

    # --- Directory ---
    if effective_mode in ("directory", "list", "tree"):
        if not resolved.exists():
            return json.dumps({"success": False, "error": f"Path not found: {path}"})
        if not resolved.is_dir():
            return json.dumps({"success": False, "error": f"Not a directory: {path}"})

        glob_patterns = [glob] if glob else None
        is_ignored = create_ignore_matcher(resolved) if respectIgnore else (lambda _: False)

        all_entries = _collect_entries(
            resolved,
            depth=depth,
            details=details,
            mode=effective_mode,
            types=types,
            glob_patterns=glob_patterns,
            exclude=exclude,
            is_ignored=is_ignored,
        )
        paginated = all_entries[offset : offset + limit] if limit else all_entries[offset:]
        total = sum(1 for _ in resolved.rglob("*")) if depth > 1 else sum(1 for _ in resolved.iterdir())
        dirs = sum(1 for e in paginated if e["kind"] == "directory")
        files = sum(1 for e in paginated if e["kind"] == "file")
        return json.dumps({
            "success": True,
            "path": path,
            "type": "directory",
            "entries": paginated,
            "summary": f"{len(paginated)} entries ({dirs} dirs, {files} files)",
            "stats": {"total": total, "returned": len(paginated), "offset": offset},
        })

    # --- File content ---
    if not resolved.exists():
        return json.dumps({"success": False, "error": f"Path not found: {path}"})
    if not resolved.is_file():
        return json.dumps({"success": False, "error": f"Not a file: {path}"})

    content = _read_file_content(resolved, lines)
    if isinstance(content, str):
        return json.dumps({"success": False, "error": content})

    hint = (
        f"File has {content['totalLines']} lines total. "
        "Use 'lines' parameter to read specific ranges."
        if content["truncated"]
        else None
    )
    return json.dumps({
        "success": True,
        "path": path,
        "type": "file",
        "content": content,
        **({"hint": hint} if hint else {}),
    })
