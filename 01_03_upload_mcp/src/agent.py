# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agent loop — orchestrates the tool-calling workflow for file uploads.

Flow: query → model → (tool calls → resolve file refs → MCP → results → model) → final answer

The model can request tool calls in its response. When it does, we resolve
any {{file:path}} placeholders in the arguments, execute via the MCP client,
feed the results back, and let the model continue. Repeats until the model
produces a plain text answer or we hit MAX_STEPS.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/agent.js`

"""

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from .ai import chat
from .files.resolver import resolve_file_refs
from .helpers.logger import log
from .mcp.client import call_mcp_tool, mcp_tools_to_openai

MAX_STEPS = 50
_WORKSPACE_ROOT = Path(__file__).parent.parent / "workspace"


async def run(
    conversation: list[dict],
    *,
    mcp_clients: dict,
    mcp_tools: list[Any],
    model: str,
    instructions: str,
    max_output_tokens: int,
) -> dict:
    """Run the upload agent loop.

    Args:
        conversation: Initial conversation list (user message).
        mcp_clients: Dict of server name → ``ClientSession``.
        mcp_tools: Prefixed tool objects from ``list_all_mcp_tools()``.
        model: Model identifier.
        instructions: System instructions for the model.
        max_output_tokens: Token cap for responses.

    Returns:
        Dict with ``text`` (final answer) and ``conversation`` (full history).

    Raises:
        RuntimeError: If MAX_STEPS is exceeded.
    """
    tools = mcp_tools_to_openai(mcp_tools)

    async def execute_tool(call: dict) -> dict:
        raw_args = json.loads(call["arguments"])
        # Resolve {{file:path}} placeholders before calling the MCP server
        args = await resolve_file_refs(raw_args, _WORKSPACE_ROOT)

        log.tool(call["name"], raw_args)  # Log pre-resolved args for readability

        try:
            result = await call_mcp_tool(mcp_clients, call["name"], args)
            output = json.dumps(result)
            log.tool_result(call["name"], True, output)
            return {"type": "function_call_output", "call_id": call["call_id"], "output": output}
        except Exception as error:
            output = json.dumps({"error": str(error)})
            log.tool_result(call["name"], False, str(error))
            return {"type": "function_call_output", "call_id": call["call_id"], "output": output}

    current = list(conversation)

    for step in range(MAX_STEPS):
        log.api(f"Step {step + 1}", len(current))
        response = await chat(
            model=model,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            input=current,
            tools=tools,
        )
        log.api_done(response.get("usage"))

        calls = [item for item in response.get("output", []) if item.get("type") == "function_call"]

        if not calls:
            # No tool calls → extract final text answer
            output_text = (
                response.get("output_text")
                or next(
                    (
                        (item.get("content") or [{}])[0].get("text")
                        for item in response.get("output", [])
                        if item.get("type") == "message"
                    ),
                    None,
                )
                or "No response"
            )
            log.response(output_text)
            return {"text": output_text, "conversation": current}

        results = await asyncio.gather(*[execute_tool(call) for call in calls])
        current = [*current, *response["output"], *results]

    raise RuntimeError(f"Tool loop did not finish within {MAX_STEPS} steps.")
