# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Tool definitions and async handlers for the Daily Ops agent: get_mail,
get_calendar, get_tasks, get_notes, read_file, write_file, and delegate.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      src/tools.ts


"""

import json
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Workspace root is always 02_04_ops/workspace/ relative to this module's root
WORKSPACE: Path = Path(__file__).parent.parent / "workspace"


def _is_path_safe(relative_path: str) -> bool:
    """Check that a relative path stays within the workspace directory.

    Uses Path.resolve() + Path.relative_to() — raises ValueError when the
    resolved path escapes the workspace, replacing the JS relative()+startsWith('..')
    pattern.

    Args:
        relative_path: Path string relative to workspace root.

    Returns:
        True when the resolved path is inside WORKSPACE, False otherwise.
    """
    try:
        full = (WORKSPACE / relative_path).resolve()
        full.relative_to(WORKSPACE.resolve())
        return True
    except ValueError:
        return False


async def _safe_read_json(file_path: Path) -> str:
    """Read and re-serialise a JSON file, returning errors as strings.

    Args:
        file_path: Absolute path to the JSON file.

    Returns:
        Compact JSON string on success, or ``Error: <message>`` on failure.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
        parsed = json.loads(text)
        return json.dumps(parsed)
    except Exception as exc:
        return f"Error: {exc}"


ToolHandler = Callable[[dict[str, Any]], Any]


class Tool:
    """Container for an OpenAI function tool definition and its async handler.

    Attributes:
        definition: Dict matching OpenAI function schema (name, description,
            parameters).
        handler: Async callable that receives parsed args and returns a string.
    """

    def __init__(self, definition: dict[str, Any], handler: ToolHandler) -> None:
        self.definition = definition
        self.handler = handler


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _make_source_reader(filename: str) -> ToolHandler:
    """Factory for source-file reader handlers.

    All four ``get_*`` tools read a single JSON file from ``workspace/sources/``
    and differ only in the filename. This factory closes over the filename to
    avoid four structurally identical functions.

    Args:
        filename: JSON filename inside ``workspace/sources/`` (e.g. ``mail.json``).

    Returns:
        Async handler that reads the given file and returns compact JSON.
    """
    async def _handler(args: dict[str, Any]) -> str:
        return await _safe_read_json(WORKSPACE / "sources" / filename)
    return _handler


async def _handle_read_file(args: dict[str, Any]) -> str:
    """Read a text file from the workspace directory.

    Args:
        args: Must contain ``path`` (str) relative to workspace root.

    Returns:
        File contents as a string, or ``Error: <message>`` on failure.
    """
    path = args.get("path")
    if not isinstance(path, str):
        return "Error: path must be a string"
    if not _is_path_safe(path):
        return "Error: Path escapes workspace"
    try:
        return (WORKSPACE / path).read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error: {exc}"


async def _handle_write_file(args: dict[str, Any]) -> str:
    """Write text content to a file in the workspace directory.

    Creates intermediate directories automatically.

    Args:
        args: Must contain ``path`` (str) and ``content`` (str).

    Returns:
        Confirmation string ``Wrote <path>``, or ``Error: <message>`` on failure.
    """
    path = args.get("path")
    content = args.get("content")
    if not isinstance(path, str):
        return "Error: path must be a string"
    if not isinstance(content, str):
        return "Error: content must be a string"
    if not _is_path_safe(path):
        return "Error: Path escapes workspace"
    try:
        full_path = WORKSPACE / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.info("Wrote workspace file: %s", path)
        return f"Wrote {path}"
    except Exception as exc:
        return f"Error: {exc}"


async def _handle_delegate(args: dict[str, Any]) -> str:
    # Delegation is intercepted by the agent loop before reaching this handler.
    # This is a fallback that should not normally be called.
    return json.dumps(args)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

tools: list[Tool] = [
    Tool(
        definition={
            "name": "get_mail",
            "description": "Read all emails from the mail inbox. Returns JSON array.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_make_source_reader("mail.json"),
    ),
    Tool(
        definition={
            "name": "get_calendar",
            "description": "Read all calendar events. Returns JSON array.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_make_source_reader("calendar.json"),
    ),
    Tool(
        definition={
            "name": "get_tasks",
            "description": "Read all tasks. Returns JSON array.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_make_source_reader("tasks.json"),
    ),
    Tool(
        definition={
            "name": "get_notes",
            "description": "Read all notes. Returns JSON array.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_make_source_reader("notes.json"),
    ),
    Tool(
        definition={
            "name": "read_file",
            "description": (
                "Read a file from the workspace directory. "
                "Path is relative to workspace root (no 'workspace/' prefix)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root",
                    }
                },
                "required": ["path"],
            },
        },
        handler=_handle_read_file,
    ),
    Tool(
        definition={
            "name": "write_file",
            "description": (
                "Write content to a file in the workspace directory. "
                "Creates parent directories if needed. "
                "Path is relative to workspace root (no 'workspace/' prefix)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
        handler=_handle_write_file,
    ),
    Tool(
        definition={
            "name": "delegate",
            "description": (
                "Delegate a task to a specialist agent by name. "
                "The agent loop intercepts this call and runs the sub-agent recursively."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Name of the agent to delegate to",
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the sub-agent",
                    },
                },
                "required": ["agent", "task"],
            },
        },
        handler=_handle_delegate,
    ),
]


def find_tool(name: str) -> Tool | None:
    """Look up a tool by its function name.

    Args:
        name: Tool function name to search for.

    Returns:
        Matching :class:`Tool` or ``None`` if not found.
    """
    return next((t for t in tools if t.definition["name"] == name), None)
