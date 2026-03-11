# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agentic loop — chat → tools → results → repeat until done.
Processes queries using the MCP client's tool set.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/agent.js`

"""

import asyncio
import json
from typing import Any

from mcp import ClientSession

from .helpers.api import chat, extract_tool_calls, extract_text
from .helpers.logger import log
from .mcp.client import call_mcp_tool, mcp_tools_to_openai

MAX_STEPS = 80


async def _run_tool(mcp_client: ClientSession, tool_call: dict) -> dict:
    """Execute a single tool call via the MCP client.

    Args:
        mcp_client: Connected MCP session.
        tool_call: Function call item from the Responses API output.

    Returns:
        A ``function_call_output`` dict to append to the conversation.
    """
    args = json.loads(tool_call["arguments"])
    log.tool(tool_call["name"], args)

    try:
        result = await call_mcp_tool(mcp_client, tool_call["name"], args)
        output = json.dumps(result)
        log.tool_result(tool_call["name"], True, output)
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": output,
        }
    except Exception as error:
        output = json.dumps({"error": str(error)})
        log.tool_result(tool_call["name"], False, str(error))
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": output,
        }


async def run(query: str, *, mcp_client: ClientSession, mcp_tools: list[Any]) -> dict:
    """Run the agentic loop for a given query.

    Args:
        query: User query / task description.
        mcp_client: Connected MCP session with file system tools.
        mcp_tools: List of MCP tool objects from ``list_tools()``.

    Returns:
        Dict with ``response`` (final text) and ``tool_calls`` (history list).

    Raises:
        RuntimeError: If ``MAX_STEPS`` is exceeded without a final answer.
    """
    tools = mcp_tools_to_openai(mcp_tools)
    messages = [{"role": "user", "content": query}]
    history: list[dict] = []

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(input=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            log.response(text)
            return {"response": text, "toolCalls": history}

        messages.extend(response["output"])

        for tc in tool_calls:
            history.append({"name": tc["name"], "arguments": json.loads(tc["arguments"])})

        results = await asyncio.gather(
            *[_run_tool(mcp_client, tc) for tc in tool_calls]
        )
        messages.extend(results)

    raise RuntimeError(f"Max steps ({MAX_STEPS}) reached")
