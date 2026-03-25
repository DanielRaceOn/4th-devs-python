# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Tool definitions for the agent — read_file and write_file, both sandboxed
to the workspace directory.

Each tool has a ``definition`` dict (passed to the Responses API as a function
tool schema) and an async ``handler`` callable that executes the tool.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/agent/tools.ts


"""

from pathlib import Path
from typing import Any, Callable

from ..config import WORKSPACE
from ..helpers.utils import format_error


def _is_path_safe(path: str) -> bool:
    """Check that *path* resolves inside the workspace sandbox.

    Args:
        path: File path relative to the workspace root.

    Returns:
        ``True`` if the resolved path stays within ``WORKSPACE``.
    """
    try:
        full = (Path(WORKSPACE) / path).resolve()
        full.relative_to(Path(WORKSPACE).resolve())
        return True
    except ValueError:
        return False


async def _handle_read_file(args: dict[str, Any]) -> str:
    """Read a sandboxed workspace file and return its contents.

    Args:
        args: Dict with key ``path`` (str, relative to workspace root).

    Returns:
        File contents as a string, or an error message string on failure.
    """
    path = args.get("path", "") if isinstance(args.get("path"), str) else ""
    if not path or not _is_path_safe(path):
        return "Error: invalid or unsafe path"
    try:
        return (Path(WORKSPACE) / path).read_text(encoding="utf-8")
    except Exception as err:
        return f"Error: {format_error(err)}"


async def _handle_write_file(args: dict[str, Any]) -> str:
    """Write content to a sandboxed workspace file, creating directories as needed.

    Args:
        args: Dict with keys ``path`` (str) and ``content`` (str).

    Returns:
        Confirmation string on success, or an error message string on failure.
    """
    path = args.get("path", "") if isinstance(args.get("path"), str) else ""
    content = args.get("content", "") if isinstance(args.get("content"), str) else ""
    if not path or not _is_path_safe(path):
        return "Error: invalid or unsafe path"
    try:
        full = Path(WORKSPACE) / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return f"Wrote {path}"
    except Exception as err:
        return f"Error: {format_error(err)}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

# Each entry: definition (Responses API schema) + handler (async callable)
tools: list[dict] = [
    {
        "definition": {
            "type": "function",
            "name": "read_file",
            "description": "Read a file from the workspace directory. Path is relative to workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace"},
                },
                "required": ["path"],
            },
        },
        "handler": _handle_read_file,
    },
    {
        "definition": {
            "type": "function",
            "name": "write_file",
            "description": "Write content to a file in the workspace directory. Creates directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
        "handler": _handle_write_file,
    },
]

_tools_by_name: dict[str, dict] = {t["definition"]["name"]: t for t in tools}


def find_tool(name: str) -> dict | None:
    """Look up a tool by name.

    Args:
        name: Tool function name.

    Returns:
        Tool dict (with ``definition`` and ``handler``) or ``None``.
    """
    return _tools_by_name.get(name)


def resolve_agent_tools(tool_names: list[str]) -> list[dict]:
    """Build the list of Responses API tool schemas for a given name list.

    Only names that exist in the registry are included; unknown names are
    silently skipped (mirrors the JS behaviour).

    Args:
        tool_names: Names declared in the agent template front-matter.

    Returns:
        List of ``ResolvedTool`` dicts ready for the ``tools`` field in the
        Responses API payload.
    """
    resolved: list[dict] = []
    for name in tool_names:
        tool = _tools_by_name.get(name)
        if not tool:
            continue
        d = tool["definition"]
        resolved.append(
            {
                "type": "function",
                "name": d["name"],
                "description": d["description"],
                "parameters": d["parameters"],
                "strict": False,
            }
        )
    return resolved
