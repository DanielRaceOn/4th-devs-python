# -*- coding: utf-8 -*-

#   index.py

"""
### Description:
Agent loop — executes the chat → tool calls → results cycle until the model
produces a final text response or the step limit is reached.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/agent/index.js`

"""

import asyncio
import json

from ..helpers.api import chat, extract_tool_calls, extract_text, extract_reasoning
from ..helpers.logger import log

MAX_STEPS = 30


async def _run_tool(tools: dict, tool_call: dict) -> dict:
    """Execute a single tool call and return the function_call_output message.

    Args:
        tools: Tool registry from ``create_tools()``.
        tool_call: A function_call item from the response output.

    Returns:
        Function-call output dict for inclusion in the next API request.
    """
    args = json.loads(tool_call.get("arguments", "{}"))
    output = await tools["handle"](tool_call["name"], args)
    return {
        "type": "function_call_output",
        "call_id": tool_call["call_id"],
        "output": output,
    }


async def run(
    query: str,
    *,
    tools: dict,
    conversation_history: list | None = None,
) -> dict:
    """Run the agent loop for a single user query.

    Sends messages to the Responses API, executes any tool calls in parallel,
    appends results, and repeats until the model replies without tool calls
    or ``MAX_STEPS`` is reached.

    Args:
        query: User query string.
        tools: Tool registry dict from ``create_tools()``.
        conversation_history: Prior conversation messages (cumulative).

    Returns:
        Dict with ``response`` (str) and ``conversation_history`` (updated list).

    Raises:
        RuntimeError: If ``MAX_STEPS`` is exceeded.
    """
    history = list(conversation_history or [])
    messages = [*history, {"role": "user", "content": query}]
    tool_defs = tools["definitions"]

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(input=messages, tools=tool_defs)
        log.api_done(response.get("usage"))
        log.reasoning(extract_reasoning(response))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            log.response(text)
            messages.extend(response.get("output", []))
            return {"response": text, "conversation_history": messages}

        # Append model output before executing tools
        messages.extend(response.get("output", []))

        # Execute all tool calls in parallel
        results = await asyncio.gather(*[_run_tool(tools, tc) for tc in tool_calls])
        messages.extend(results)

    raise RuntimeError(f"Max steps ({MAX_STEPS}) reached")


def create_conversation() -> dict:
    """Create a fresh conversation context.

    Returns:
        Dict with an empty ``history`` list.
    """
    return {"history": []}
