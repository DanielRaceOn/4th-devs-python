# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Agent tool definitions and executor — mirrors src/agent/tools.ts.

Provides:
  - ``TOOL_DEFINITIONS`` — OpenAI function-tool schemas for ``get_current_time``
    and ``sum_numbers``.
  - ``execute_tool(name, raw_args)`` — dispatches a tool call by name and
    returns a JSON string result.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/agent/tools.ts

"""

import json
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Tool schemas (OpenAI function-tool format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Returns the current UTC date and time as an ISO 8601 string.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sum_numbers",
            "description": "Sums an array of numbers and returns the count and total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "The list of numbers to sum.",
                    }
                },
                "required": ["numbers"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _get_current_time(_args: dict[str, Any]) -> str:
    """Return the current UTC time as a JSON string.

    Args:
        _args: Ignored (no parameters).

    Returns:
        JSON string ``{"nowUtc": "<ISO 8601>"}``.
    """
    now_utc = datetime.now(tz=timezone.utc).isoformat()
    return json.dumps({"nowUtc": now_utc})


def _sum_numbers(args: dict[str, Any]) -> str:
    """Sum an array of numbers and return count + total as JSON.

    Args:
        args: Dict with key ``"numbers"`` containing a list of numbers.

    Returns:
        JSON string ``{"count": N, "sum": S}`` or ``{"error": "..."}``
        on invalid input.
    """
    numbers = args.get("numbers")
    if not isinstance(numbers, list):
        return json.dumps({"error": "numbers must be an array"})
    try:
        total = sum(float(n) for n in numbers)
        count = len(numbers)
        return json.dumps({"count": count, "sum": total})
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


_TOOL_HANDLERS: dict[str, Any] = {
    "get_current_time": _get_current_time,
    "sum_numbers": _sum_numbers,
}


async def execute_tool(name: str, raw_args: str) -> str:
    """Execute a tool by name with JSON-encoded arguments.

    Args:
        name: Tool function name (e.g. ``"get_current_time"``).
        raw_args: JSON-encoded argument object string.

    Returns:
        JSON-encoded result string.
    """
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        args: dict[str, Any] = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid arguments JSON: {exc}"})

    return handler(args)
