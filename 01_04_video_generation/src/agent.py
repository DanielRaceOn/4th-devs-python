# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agent loop — chat → tool calls → results cycle until completion.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/agent.js

"""

import json
from typing import Optional

from .api import chat, extract_tool_calls, extract_text
from .mcp.client import call_mcp_tool, mcp_tools_to_openai
from .native.tools import native_tools, is_native_tool, execute_native_tool
from .helpers.logger import log

MAX_STEPS = 50


async def run_tool(mcp_client, tool_call: dict) -> dict:
    """Execute a single tool call."""
    args = json.loads(tool_call.get("arguments", "{}"))
    log.tool(tool_call["name"], args)

    try:
        if is_native_tool(tool_call["name"]):
            result = await execute_native_tool(tool_call["name"], args)
        else:
            result = await call_mcp_tool(mcp_client, tool_call["name"], args)

        output = json.dumps(result)
        log.tool_result(tool_call["name"], True, output)
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": output,
        }

    except Exception as e:
        output = json.dumps({"error": str(e)})
        log.tool_result(tool_call["name"], False, str(e))
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": output,
        }


async def run_tools(mcp_client, tool_calls: list) -> list:
    """Execute multiple tool calls in parallel."""
    import asyncio
    return list(await asyncio.gather(*[run_tool(mcp_client, tc) for tc in tool_calls]))


async def run(
    query: str,
    mcp_client=None,
    mcp_tools: Optional[list] = None,
    conversation_history: Optional[list] = None,
) -> dict:
    """Core agentic loop.

    Args:
        query: User query
        mcp_client: MCP client for file operations
        mcp_tools: Available MCP tools
        conversation_history: Previous messages in conversation

    Returns:
        Response dict with response text, tool calls, conversation history
    """
    if mcp_tools is None:
        mcp_tools = []
    if conversation_history is None:
        conversation_history = []

    tools = mcp_tools_to_openai(mcp_tools) + native_tools
    messages = conversation_history + [{"role": "user", "content": query}]
    tool_call_history = []

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))

        response = await chat(input_messages=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            messages.extend(response.get("output", []))
            return {
                "response": text,
                "toolCalls": tool_call_history,
                "conversationHistory": messages,
            }

        messages.extend(response.get("output", []))

        for tc in tool_calls:
            tool_call_history.append({
                "name": tc["name"],
                "arguments": json.loads(tc.get("arguments", "{}")),
            })

        results = await run_tools(mcp_client, tool_calls)
        messages.extend(results)

    raise Exception(f"Max steps ({MAX_STEPS}) reached")
