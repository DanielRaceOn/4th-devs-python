# -*- coding: utf-8 -*-

#   index.py

"""
### Description:
Agent loop — executes the chat → tool calls → results cycle until the model
produces a text response or the step limit is reached.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/agent/index.js

"""

import json
from typing import Any, Dict, List, Optional, Tuple

from ..helpers.api import chat, extract_tool_calls, extract_text, extract_reasoning
from ..helpers import logger as log

MAX_STEPS = 30


async def _run_tool(tools: Dict[str, Any], tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single tool call and return a ``function_call_output`` item.

    Args:
        tools: Tool interface dict from :func:`~src.agent.tools.create_tools`.
        tool_call: A ``function_call`` output item from the API response.

    Returns:
        Dict suitable for appending to the message history as
        ``{"type": "function_call_output", "call_id": ..., "output": ...}``.
    """
    args = json.loads(tool_call["arguments"])
    output = await tools["handle"](tool_call["name"], args)
    return {
        "type": "function_call_output",
        "call_id": tool_call["call_id"],
        "output": output,
    }


async def run(
    query: str,
    tools: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Run the agent loop for a single user query.

    Sends the query to the model, executes any requested tools, appends
    results to the conversation, and repeats until the model stops calling
    tools or the step limit is reached.

    Args:
        query: The user's question or instruction.
        tools: Tool interface dict from :func:`~src.agent.tools.create_tools`.
        conversation_history: Accumulated conversation messages from previous
            turns (mutated by appending new messages).

    Returns:
        Tuple of (response_text, updated_conversation_history).

    Raises:
        RuntimeError: If the step limit is reached without a text response.
    """
    history = list(conversation_history or [])
    messages = history + [{"role": "user", "content": query}]

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(
            input_messages=messages,
            tools=tools["definitions"],
        )
        log.api_done(response.get("usage"))
        log.reasoning(extract_reasoning(response))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            log.response(text)
            messages.extend(response.get("output", []))
            return text, messages

        # Append the model's output (function_call items) to history
        messages.extend(response.get("output", []))

        # Execute all tool calls (parallel would be asyncio.gather but sequential
        # is safer for SQLite operations)
        for tc in tool_calls:
            result = await _run_tool(tools, tc)
            messages.append(result)

    raise RuntimeError(f"Max steps ({MAX_STEPS}) reached without a response")


def create_conversation() -> Dict[str, Any]:
    """Create a fresh conversation context with empty history.

    Returns:
        Dict with ``history`` key containing an empty list.
    """
    return {"history": []}
