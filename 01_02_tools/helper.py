# -*- coding: utf-8 -*-

#   helper.py

"""
### Description:
Utility helpers for tool-use examples: extracting tool calls and final text from
Responses API output, colourised console logging for questions/answers/tool calls,
and the core tool-execution + conversation-building helpers.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `helper.js`


"""

import json
import sys
from typing import Any, Callable, Dict, List

# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def get_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return all function_call items from a Responses API output array.

    Args:
        response: Raw Responses API response dict.

    Returns:
        List of function_call output items (may be empty).
    """
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def get_final_text(response: Dict[str, Any]) -> str:
    """Extract the assistant's final text reply from a Responses API response.

    Tries ``output_text`` first (a convenience field), then falls back to the
    first message item's content text.

    Args:
        response: Raw Responses API response dict.

    Returns:
        The assistant text, or ``"No response"`` if nothing found.
    """
    output_text = response.get("output_text")
    if output_text:
        return output_text

    for item in response.get("output", []):
        if item.get("type") == "message":
            content = item.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "No response")

    return "No response"


# ---------------------------------------------------------------------------
# Colourised console output
# ---------------------------------------------------------------------------

# Respect the NO_COLOR convention and non-TTY environments.
_supports_color: bool = sys.stdout.isatty() and not sys.environ.get("NO_COLOR")

_ANSI = {
    "reset": "\x1b[0m",
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
    "blue": "\x1b[34m",
    "cyan": "\x1b[36m",
    "green": "\x1b[32m",
    "magenta": "\x1b[35m",
    "yellow": "\x1b[33m",
}


def _colorize(text: str, *styles: str) -> str:
    """Wrap *text* with ANSI escape codes for the given *styles*.

    Args:
        text: Plain text to wrap.
        *styles: Style keys from the ``_ANSI`` mapping (e.g. ``"bold"``, ``"blue"``).

    Returns:
        ANSI-coloured string if colour is supported, otherwise the plain text.
    """
    if not _supports_color:
        return text
    sequence = "".join(_ANSI[s] for s in styles if s in _ANSI)
    return f"{sequence}{text}{_ANSI['reset']}"


def _label(text: str, color: str) -> str:
    return _colorize(f"[{text}]", "bold", color)


def log_question(text: str) -> None:
    """Print the user question with a ``[USER]`` label.

    Args:
        text: The question text.
    """
    print(f"{_label('USER', 'blue')} {text}\n")


def log_tool_call(name: str, args: Dict[str, Any]) -> None:
    """Print a tool invocation with its arguments.

    Args:
        name: Tool function name.
        args: Parsed arguments dict.
    """
    print(f"{_label('TOOL', 'magenta')} {_colorize(name, 'bold')}")
    print(_colorize("Arguments:", "cyan"))
    print(_colorize(json.dumps(args, indent=2), "dim"))


def log_tool_result(result: Any) -> None:
    """Print a tool's return value.

    Args:
        result: Tool result (any JSON-serialisable value).
    """
    print(_colorize("Result:", "yellow"))
    print(_colorize(json.dumps(result, indent=2), "dim"))
    print()


def log_answer(text: str) -> None:
    """Print the assistant's final answer with an ``[ASSISTANT]`` label.

    Args:
        text: The assistant text.
    """
    print(f"{_label('ASSISTANT', 'green')} {text}")


# ---------------------------------------------------------------------------
# Tool execution and conversation management
# ---------------------------------------------------------------------------


async def execute_tool_call(
    call: Dict[str, Any],
    handlers: Dict[str, Callable],
) -> Dict[str, Any]:
    """Execute a single tool call and return a function_call_output item.

    Args:
        call: A function_call item from the Responses API output.
        handlers: Mapping of tool name to its implementation.

    Returns:
        A ``function_call_output`` dict ready to append to the conversation.

    Raises:
        KeyError: If the tool name has no registered handler.
    """
    args = json.loads(call["arguments"])
    handler = handlers.get(call["name"])

    if handler is None:
        raise KeyError(f"Unknown tool: {call['name']}")

    log_tool_call(call["name"], args)
    result = await _maybe_await(handler(args))
    log_tool_result(result)

    return {
        "type": "function_call_output",
        "call_id": call["call_id"],
        "output": json.dumps(result),
    }


async def _maybe_await(value: Any) -> Any:
    """Await *value* if it is a coroutine, otherwise return it directly.

    Args:
        value: Possibly awaitable return value from a handler.

    Returns:
        Resolved value.
    """
    import inspect

    if inspect.isawaitable(value):
        return await value
    return value


async def build_next_conversation(
    conversation: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    handlers: Dict[str, Callable],
) -> List[Dict[str, Any]]:
    """Append tool calls and their results to the current conversation.

    Executes all tool calls concurrently and returns the extended conversation
    list for the next API round-trip.

    Args:
        conversation: Current list of conversation items.
        tool_calls: function_call items returned by the model.
        handlers: Mapping of tool name to its implementation.

    Returns:
        New conversation list: original items + tool calls + tool results.
    """
    import asyncio

    tool_results = await asyncio.gather(
        *[execute_tool_call(call, handlers) for call in tool_calls]
    )
    return [*conversation, *tool_calls, *tool_results]
