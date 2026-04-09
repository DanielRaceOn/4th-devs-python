# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Tool definitions and execution for the Responses API — mirrors
src/agent/tools.ts.

Defines two tools in OpenAI Responses API ``FunctionTool`` format:
  - ``get_current_time`` — returns current UTC time in ISO format
  - ``sum_numbers``      — sums a list of numbers

``execute_tool`` dispatches by name and returns a JSON-encoded string.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/agent/tools.ts

"""

import json
from datetime import datetime, timezone
from typing import Any

# Tool definitions in OpenAI Responses API FunctionTool format
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Returns current UTC time in ISO format.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "sum_numbers",
        "description": "Sums a list of numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 1,
                }
            },
            "required": ["numbers"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]


def _parse_args(raw: str) -> dict[str, Any] | None:
    """Parse a JSON string into a dict, returning None on failure.

    Args:
        raw: JSON-encoded arguments string.

    Returns:
        Parsed dict, or ``None`` if parsing fails.
    """
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return None
    except json.JSONDecodeError:
        return None


async def execute_tool(name: str, raw_args: str) -> str:
    """Dispatch a tool call by name and return a JSON-encoded result string.

    Args:
        name: Tool name (``"get_current_time"`` or ``"sum_numbers"``).
        raw_args: JSON-encoded arguments string.

    Returns:
        JSON string containing the tool result or an error description.
    """
    if name == "get_current_time":
        now_utc = datetime.now(tz=timezone.utc).isoformat()
        return json.dumps({"nowUtc": now_utc})

    if name == "sum_numbers":
        args = _parse_args(raw_args)
        if args is None:
            return json.dumps({"error": "Invalid JSON arguments"})

        raw_numbers = args.get("numbers")
        if not isinstance(raw_numbers, list):
            return json.dumps({"error": "numbers must contain at least one numeric value"})

        numbers = [n for n in raw_numbers if isinstance(n, (int, float)) and not (n != n)]
        if not numbers:
            return json.dumps({"error": "numbers must contain at least one numeric value"})

        return json.dumps({"count": len(numbers), "sum": sum(numbers)})

    return json.dumps({"error": f"Unknown tool: {name}"})
