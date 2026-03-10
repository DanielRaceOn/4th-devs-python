# -*- coding: utf-8 -*-

#   executor.py

"""
### Description:
Tool-use execution loop for 01_02_tool_use.  ``process_query`` runs a single
natural-language query through the Responses API, dispatching any tool calls
requested by the model until it produces a final text answer or the round limit
is reached.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/executor.js`


"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

from .api import chat, extract_text, extract_tool_calls

MAX_TOOL_ROUNDS = 10


def _log_query(query: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print("=" * 60)


def _log_result(text: str) -> None:
    print(f"\nA: {text}")


async def _execute_tool_calls(
    tool_calls: List[Dict[str, Any]],
    handlers: Dict[str, Callable],
) -> List[Dict[str, Any]]:
    """Execute all tool calls concurrently and return function_call_output items.

    Args:
        tool_calls: List of function_call items from the model response.
        handlers: Mapping of tool name to its async (or sync) implementation.

    Returns:
        List of function_call_output dicts ready to append to the conversation.
    """
    print(f"\nTool calls: {len(tool_calls)}")

    async def _run_one(call: Dict[str, Any]) -> Dict[str, Any]:
        args = json.loads(call["arguments"])
        print(f"  → {call['name']}({json.dumps(args)})")

        try:
            handler = handlers.get(call["name"])
            if handler is None:
                raise KeyError(f"Unknown tool: {call['name']}")

            result = handler(args)
            if asyncio.iscoroutine(result):
                result = await result

            print("    ✓ Success")
            return {
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": json.dumps(result),
            }
        except Exception as exc:
            print(f"    ✗ Error: {exc}")
            return {
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": json.dumps({"error": str(exc)}),
            }

    return list(await asyncio.gather(*[_run_one(c) for c in tool_calls]))


async def process_query(
    query: str,
    *,
    model: str,
    tools: List[Dict[str, Any]],
    handlers: Dict[str, Callable],
    instructions: Optional[str] = None,
) -> str:
    """Send *query* to the model and run the tool-use loop until a final answer.

    Each query is handled as a fresh, isolated conversation — tool-use state is
    not carried between successive calls to this function.

    Args:
        query: Natural-language question or instruction for the model.
        model: Resolved model identifier.
        tools: Tool definitions to include in the request.
        handlers: Mapping of tool name → implementation callable.
        instructions: Optional system-level instructions for the assistant.

    Returns:
        Final text answer from the model (or ``"Max tool rounds reached"``).
    """
    _log_query(query)
    conversation: List[Dict[str, Any]] = [{"role": "user", "content": query}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = await chat(
            model=model,
            input_=conversation,
            tools=tools,
            instructions=instructions,
        )
        calls = extract_tool_calls(response)

        if not calls:
            text = extract_text(response) or "No response"
            _log_result(text)
            return text

        tool_results = await _execute_tool_calls(calls, handlers)
        conversation = [*conversation, *calls, *tool_results]

    _log_result("Max tool rounds reached")
    return "Max tool rounds reached"
