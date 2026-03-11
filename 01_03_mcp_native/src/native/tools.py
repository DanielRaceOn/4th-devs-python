# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions — plain Python functions in OpenAI function format.
These are "native" tools that run directly in the same process, as opposed
to MCP tools which are called through the protocol. The agent treats both
identically via the unified handler map.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/native/tools.js`

"""

from typing import Any

# Tool schemas in OpenAI function-calling format
native_tools: list[dict] = [
    {
        "type": "function",
        "name": "calculate",
        "description": "Perform a basic math calculation",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The math operation to perform",
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"},
            },
            "required": ["operation", "a", "b"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "uppercase",
        "description": "Convert text to uppercase",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _calculate(operation: str, a: float, b: float) -> Any:
    ops = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: {"error": "Division by zero"} if b == 0 else a / b,
    }
    result = ops[operation]()
    if isinstance(result, dict):
        return result
    return {"result": result, "expression": f"{a} {operation} {b}"}


def _uppercase(text: str) -> dict:
    return {"result": text.upper()}


# Map of tool name → sync callable (the agent loop handles async wrapping)
native_handlers: dict = {
    "calculate": lambda args: _calculate(args["operation"], args["a"], args["b"]),
    "uppercase": lambda args: _uppercase(args["text"]),
}
