# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agent loop — processes queries using a unified set of tool handlers.
The agent doesn't know whether a tool is served by MCP or native Python.
It dispatches to the handler map built by app.py. Each handler has
{execute, label} so the output shows which backend ran the tool.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/agent.js`

"""

import asyncio
import json
from typing import Any, Optional

from .ai import chat, extract_tool_calls, extract_text
from .log import (
    log_query, log_tool_call, log_tool_result,
    log_tool_error, log_tool_count, log_response,
)

MAX_TOOL_ROUNDS = 10


async def _execute_tool_call(call: dict, handlers: dict) -> dict:
    """Execute a single tool call using the unified handler map.

    Args:
        call: Function call item from the Responses API output.
        handlers: Map of tool name → ``{"execute": callable, "label": str}``.

    Returns:
        A ``function_call_output`` dict ready to append to the conversation.
    """
    args = json.loads(call["arguments"])
    handler = handlers.get(call["name"])

    if not handler:
        raise ValueError(f"Unknown tool: {call['name']}")

    log_tool_call(handler["label"], call["name"], args)

    try:
        # execute may be sync or async
        result = handler["execute"](args)
        if asyncio.iscoroutine(result):
            result = await result
        log_tool_result(result)
        return {
            "type": "function_call_output",
            "call_id": call["call_id"],
            "output": json.dumps(result),
        }
    except Exception as error:
        log_tool_error(str(error))
        return {
            "type": "function_call_output",
            "call_id": call["call_id"],
            "output": json.dumps({"error": str(error)}),
        }


def create_agent(
    *,
    model: str,
    tools: list[dict],
    instructions: str,
    handlers: dict,
) -> Any:
    """Create an agent that processes queries using mixed MCP and native tools.

    Args:
        model: Model identifier.
        tools: List of tool definitions in OpenAI format.
        instructions: System prompt / instructions for the model.
        handlers: Map of tool name → ``{"execute": callable, "label": str}``.

    Returns:
        An agent object with an async ``process_query(query)`` method.
    """
    class Agent:
        async def process_query(self, query: str) -> str:
            log_query(query)

            chat_config = {"model": model, "tools": tools, "instructions": instructions}
            conversation = [{"role": "user", "content": query}]

            for _ in range(MAX_TOOL_ROUNDS):
                response = await chat(**chat_config, input=conversation)
                tool_calls = extract_tool_calls(response)

                if not tool_calls:
                    text = extract_text(response) or "No response"
                    log_response(text)
                    return text

                log_tool_count(len(tool_calls))
                tool_results = await asyncio.gather(
                    *[_execute_tool_call(call, handlers) for call in tool_calls]
                )

                # Append model output items and tool results to conversation
                conversation = [*conversation, *response["output"], *tool_results]

            log_response("Max tool rounds reached")
            return "Max tool rounds reached"

    return Agent()
