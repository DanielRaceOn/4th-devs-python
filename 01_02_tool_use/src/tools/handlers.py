# -*- coding: utf-8 -*-

#   handlers.py

"""
### Description:
Async handler implementations for the sandboxed filesystem tools.  Each handler
receives a dict of arguments from the model, delegates to the real filesystem
via pathlib / stdlib, and returns a JSON-serialisable result dict.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/tools/handlers.js`


"""

import asyncio
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List

from ..utils.sandbox import resolve_sandbox_path


async def _list_files(args: Dict[str, Any]) -> List[Dict[str, str]]:
    """List files and directories inside the sandbox at *args["path"]*.

    Args:
        args: Must contain ``"path"`` — relative path within the sandbox.

    Returns:
        List of dicts with ``name`` and ``type`` (``"file"`` or ``"directory"``).
    """
    full_path = resolve_sandbox_path(args["path"])
    entries = []
    for entry in full_path.iterdir():
        entries.append({
            "name": entry.name,
            "type": "directory" if entry.is_dir() else "file",
        })
    return entries


async def _read_file(args: Dict[str, Any]) -> Dict[str, str]:
    """Read the text content of a sandbox file.

    Args:
        args: Must contain ``"path"`` — relative path to the file.

    Returns:
        Dict with ``"content"`` key holding the file text.
    """
    full_path = resolve_sandbox_path(args["path"])
    content = full_path.read_text(encoding="utf-8")
    return {"content": content}


async def _write_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Write *args["content"]* to a sandbox file (creates or overwrites).

    Args:
        args: Must contain ``"path"`` and ``"content"``.

    Returns:
        Dict with ``"success": True`` and a confirmation message.
    """
    full_path = resolve_sandbox_path(args["path"])
    # Ensure parent directories exist before writing.
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(args["content"], encoding="utf-8")
    return {"success": True, "message": f"File written: {args['path']}"}


async def _delete_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a file from the sandbox.

    Args:
        args: Must contain ``"path"`` — relative path to the file.

    Returns:
        Dict with ``"success": True`` and a confirmation message.
    """
    full_path = resolve_sandbox_path(args["path"])
    full_path.unlink()
    return {"success": True, "message": f"File deleted: {args['path']}"}


async def _create_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a directory (and any missing parents) inside the sandbox.

    Args:
        args: Must contain ``"path"`` — relative directory path.

    Returns:
        Dict with ``"success": True`` and a confirmation message.
    """
    full_path = resolve_sandbox_path(args["path"])
    full_path.mkdir(parents=True, exist_ok=True)
    return {"success": True, "message": f"Directory created: {args['path']}"}


async def _file_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata for a file or directory inside the sandbox.

    Args:
        args: Must contain ``"path"`` — relative path to inspect.

    Returns:
        Dict with ``size``, ``isDirectory``, ``created``, and ``modified`` (ISO-8601).
    """
    full_path = resolve_sandbox_path(args["path"])
    stat = full_path.stat()
    return {
        "size": stat.st_size,
        "isDirectory": full_path.is_dir(),
        # Convert timestamps to UTC ISO-8601 strings.
        "created": _ts_to_iso(stat.st_ctime),
        "modified": _ts_to_iso(stat.st_mtime),
    }


def _ts_to_iso(timestamp: float) -> str:
    """Convert a POSIX timestamp to an ISO-8601 UTC string.

    Args:
        timestamp: POSIX timestamp (seconds since epoch).

    Returns:
        UTC datetime string in ISO-8601 format.
    """
    from datetime import datetime

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


# Public mapping consumed by executor.py
handlers: Dict[str, Any] = {
    "list_files": _list_files,
    "read_file": _read_file,
    "write_file": _write_file,
    "delete_file": _delete_file,
    "create_directory": _create_directory,
    "file_info": _file_info,
}
