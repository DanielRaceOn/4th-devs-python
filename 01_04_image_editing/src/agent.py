# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agent loop — chat → tool calls → results cycle until completion.
Supports both MCP and native tools with persistent conversation history across REPL turns.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/agent.js

"""

import asyncio
import json
from typing import Optional

from .api import chat, extract_tool_calls, extract_text
from .mcp.client import McpSession, call_mcp_tool, mcp_tools_to_openai
from .native.tools import native_tools, is_native_tool, execute_native_tool
from .helpers.logger import log

MAX_STEPS = 50


async def _run_tool(mcp_client: Optional[McpSession], tool_call: dict) -> dict:
    """Execute a single tool call — native or MCP.

    Args:
        mcp_client: Connected MCP session (used for non-native tools).
        tool_call: Function call dict from the Responses API output.

    Returns:
        ``function_call_output`` dict ready to append to the message history.
    """
    args = json.loads(tool_call.get("arguments", "{}"))
    log.tool(tool_call["name"], args)

    try:
        if is_native_tool(tool_call["name"]):
            result = await execute_native_tool(tool_call["name"], args)
        else:
            result = await call_mcp_tool(mcp_client, tool_call["name"], args)

        output = json.dumps(result)
        log.tool_result(tool_call["name"], True, output)
        return {"type": "function_call_output", "call_id": tool_call["call_id"], "output": output}

    except Exception as error:
        output = json.dumps({"error": str(error)})
        log.tool_result(tool_call["name"], False, str(error))
        return {"type": "function_call_output", "call_id": tool_call["call_id"], "output": output}


async def _run_tools(mcp_client: Optional[McpSession], tool_calls: list) -> list:
    """Execute all tool calls from a single step in parallel.

    Args:
        mcp_client: Connected MCP session.
        tool_calls: List of function_call dicts.

    Returns:
        List of ``function_call_output`` dicts.
    """
    return list(await asyncio.gather(*[_run_tool(mcp_client, tc) for tc in tool_calls]))


async def run(
    query: str,
    *,
    mcp_client: Optional[McpSession] = None,
    mcp_tools: Optional[list] = None,
    conversation_history: Optional[list] = None,
) -> dict:
    """Run the agent loop for a single user query.

    The conversation history is extended with each step so callers (the REPL)
    can pass it back on the next turn to maintain multi-turn context.

    Args:
        query: User's text input for this turn.
        mcp_client: Connected MCP session for file operations.
        mcp_tools: MCP tool definition objects (from ``list_mcp_tools``).
        conversation_history: Previous conversation messages to prepend.

    Returns:
        Dict with ``response`` (assistant text) and ``conversation_history``
        (full updated message list including this turn).

    Raises:
        Exception: If ``MAX_STEPS`` is reached without a final text response.
    """
    tools = mcp_tools_to_openai(mcp_tools or []) + native_tools
    messages = [*(conversation_history or []), {"role": "user", "content": query}]

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(input_messages=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            # Final response — no more tool calls
            text = extract_text(response) or "No response"
            messages.extend(response.get("output", []))
            return {"response": text, "conversation_history": messages}

        messages.extend(response.get("output", []))

        results = await _run_tools(mcp_client, tool_calls)
        messages.extend(results)

    raise Exception(f"Max steps ({MAX_STEPS}) reached")
