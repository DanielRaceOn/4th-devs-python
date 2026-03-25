# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agentic loop for the video processing agent. Executes the chat → tool calls → results
cycle until the model returns a final text response or the step limit is reached.
Supports both native video tools and MCP file tools, with persistent conversation
history across REPL turns.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/agent.js`


"""

import asyncio
import json
import logging
from typing import Any

from mcp import ClientSession

from .helpers.api import chat, extract_text, extract_tool_calls
from .helpers.logger import log
from .mcp.client import call_mcp_tool, mcp_tools_to_openai
from .native.tools import execute_native_tool, is_native_tool, native_tools

logger = logging.getLogger(__name__)

MAX_STEPS: int = 50


async def _run_tool(session: ClientSession, tool_call: dict[str, Any]) -> dict[str, Any]:
    """Execute a single tool call and return a function_call_output message.

    Dispatches to native handlers or the MCP session based on tool name.
    Tool call arguments arrive as a JSON string (Responses API format) and are
    parsed before dispatch.

    Args:
        session: Active MCP client session (used for non-native tools).
        tool_call: Function call item from the Responses API response output.

    Returns:
        Dict with ``type: "function_call_output"``, ``call_id``, and ``output``.
    """
    name: str = tool_call.get("name", "")
    call_id: str = tool_call.get("call_id", "")
    raw_args: str = tool_call.get("arguments", "{}")

    try:
        args: dict[str, Any] = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError:
        args = {}

    log.tool(name, args)

    try:
        if is_native_tool(name):
            result = await execute_native_tool(name, args)
        else:
            result = await call_mcp_tool(session, name, args)

        output = json.dumps(result)
        log.tool_result(name, True, output)
        return {"type": "function_call_output", "call_id": call_id, "output": output}

    except Exception as exc:
        output = json.dumps({"error": str(exc)})
        log.tool_result(name, False, str(exc))
        return {"type": "function_call_output", "call_id": call_id, "output": output}


async def _run_tools(
    session: ClientSession, tool_calls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Execute all tool calls in parallel and collect results.

    Args:
        session: Active MCP client session.
        tool_calls: List of function_call items from the API response.

    Returns:
        List of function_call_output dicts, one per tool call.
    """
    return list(await asyncio.gather(*[_run_tool(session, tc) for tc in tool_calls]))


async def run(
    query: str,
    *,
    session: ClientSession,
    mcp_tools: list[Any],
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the agent on a user query.

    Executes the chat → tool-calls → results loop for up to ``MAX_STEPS`` steps.
    Conversation history is accumulated and returned so the REPL can persist it
    across follow-up turns.

    The Responses API uses ``input`` (not ``messages``) and returns an ``output``
    array. Tool results are injected back into ``input`` as
    ``function_call_output`` items alongside the model's function_call items.

    Args:
        query: User query string.
        session: Active MCP client session.
        mcp_tools: MCP Tool objects from ``list_mcp_tools()``.
        conversation_history: Previous ``input`` items for multi-turn support.

    Returns:
        Dict with ``response`` (final text) and ``conversation_history`` (full
        input list for the next turn).

    Raises:
        RuntimeError: When the step limit is reached without a final answer.
    """
    if conversation_history is None:
        conversation_history = []

    # Combine MCP and native tools in OpenAI function format
    tools = [*mcp_tools_to_openai(mcp_tools), *native_tools]

    # Append the new user message to the accumulated history
    messages: list[dict[str, Any]] = [
        *conversation_history,
        {"role": "user", "content": query},
    ]

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(input=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            # No tool calls — model produced a final answer.
            # Push all output items into history so the next turn has context.
            messages.extend(response.get("output") or [])
            text = extract_text(response) or "No response"
            return {"response": text, "conversation_history": messages}

        # Append assistant output (tool calls + any text) to message history
        messages.extend(response.get("output") or [])

        # Execute tool calls in parallel and append results
        results = await _run_tools(session, tool_calls)
        messages.extend(results)

    raise RuntimeError(f"Max steps ({MAX_STEPS}) reached without a final response")


def create_conversation() -> dict[str, list]:
    """Create a new empty conversation context.

    Returns:
        Dict with an empty ``history`` list, matching the JS ``createConversation``.
    """
    return {"history": []}
