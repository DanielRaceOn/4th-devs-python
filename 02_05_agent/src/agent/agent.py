# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Main agent loop — loads an agent template, runs the observer/reflector memory
cycle before each Responses API call, dispatches tool calls, and returns the
final text response.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/agent/agent.ts


"""

import httpx

try:
    import frontmatter  # type: ignore
except ImportError:
    frontmatter = None  # handled in load_agent

from ..config import (
    WORKSPACE,
    AGENT_MAX_TURNS,
    DEFAULT_AGENT_NAME,
    DEFAULT_MEMORY_CONFIG,
)
from ..ai.tokens import estimate_messages_tokens, track_usage, get_calibration
from ..ai.response import get_response_message_text
from ..helpers.utils import truncate, parse_args, format_error
from ..helpers.log import log, log_error
from ..memory.processor import process_memory
from .tools import find_tool, resolve_agent_tools


async def _load_agent(name: str) -> dict:
    """Load an agent template from ``workspace/agents/{name}.agent.md``.

    The file uses YAML front-matter for metadata (name, model, tools) and the
    Markdown body as the system prompt.

    Args:
        name: Agent base name (without the ``.agent.md`` suffix).

    Returns:
        AgentTemplate dict with ``name``, ``model``, ``tools``, ``system_prompt``.

    Raises:
        RuntimeError: If ``python-frontmatter`` is not installed.
    """
    if frontmatter is None:
        raise RuntimeError(
            "python-frontmatter is required to load agent templates. "
            "Install with: pip install python-frontmatter"
        )
    path = WORKSPACE / "agents" / f"{name}.agent.md"
    post = frontmatter.load(str(path))
    return {
        "name": post.metadata.get("name", name),
        "model": post.metadata.get("model", "gpt-4.1-mini")
        if isinstance(post.metadata.get("model"), str)
        else "gpt-4.1-mini",
        "tools": post.metadata.get("tools", [])
        if isinstance(post.metadata.get("tools"), list)
        else [],
        "system_prompt": post.content.strip(),
    }


def _apply_response_output(session: dict, output: list[dict]) -> list[dict]:
    """Append LLM output items to ``session["messages"]``.

    Text message items are converted to ``{"role": "assistant", "content": ...}``.
    Function-call items are appended as-is and also collected into the returned
    list so the caller can dispatch them.

    Args:
        session: Current session dict (mutated in place).
        output: ``response.output`` list from the Responses API.

    Returns:
        List of pending function-call items that need execution.
    """
    pending_calls: list[dict] = []

    for item in output:
        if item.get("type") == "message":
            text = get_response_message_text(item)
            if text:
                session["messages"].append({"role": "assistant", "content": text})
            continue

        if item.get("type") == "function_call":
            call = {
                "type": "function_call",
                "call_id": item["call_id"],
                "name": item["name"],
                "arguments": item["arguments"],
            }
            session["messages"].append(call)
            pending_calls.append(call)

    return pending_calls


async def _execute_tool_call(session: dict, call: dict) -> None:
    """Execute a single tool call and append the result to ``session["messages"]``.

    Args:
        session: Current session dict (mutated in place).
        call: FunctionCallItem dict with ``call_id``, ``name``, ``arguments``.
    """
    try:
        args = parse_args(call["arguments"])
    except Exception as err:
        log_error("agent", f"Tool: {call['name']} — bad arguments:", err)
        session["messages"].append(
            {
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": f"Error parsing arguments: {format_error(err)}",
            }
        )
        return

    log("agent", f"Tool: {call['name']}({truncate(str(args))})")

    tool = find_tool(call["name"])
    if tool:
        output = await tool["handler"](args)
    else:
        output = f"Unknown tool: {call['name']}"

    session["messages"].append(
        {"type": "function_call_output", "call_id": call["call_id"], "output": output}
    )


async def run_agent(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    session: dict,
    user_message: str,
    agent_name: str = DEFAULT_AGENT_NAME,
) -> dict:
    """Run the agent loop for a single user message.

    Appends *user_message* to the session, then runs up to
    ``AGENT_MAX_TURNS`` iterations of: observe/reflect memory → LLM call →
    tool dispatch.  Returns when the LLM produces no more tool calls.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        session: Current session dict (mutated in place).
        user_message: The user's text input for this turn.
        agent_name: Agent template name to load (default ``"alice"``).

    Returns:
        AgentResult dict with ``response`` (str) and ``usage`` (dict).
    """
    from ..config import resolve_model_for_provider

    template = await _load_agent(agent_name)
    model = resolve_model_for_provider(template["model"])
    responses_tools = resolve_agent_tools(template["tools"])
    cal = session["memory"].get("calibration")

    session["messages"].append({"role": "user", "content": user_message})
    # Reset per-request observer flag
    session["memory"]["_observer_ran_this_request"] = False

    totals = {"estimated": 0, "actual": 0}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **extra_headers,
    }

    def _build_usage(turns: int) -> dict:
        return {
            "total_estimated_tokens": totals["estimated"],
            "total_actual_tokens": totals["actual"],
            "calibration": get_calibration(cal),
            "turns": turns,
        }

    for turn in range(AGENT_MAX_TURNS):
        context = await process_memory(
            client, api_url, api_key, extra_headers, session, template["system_prompt"], DEFAULT_MEMORY_CONFIG
        )
        estimated = estimate_messages_tokens(context["messages"], cal)
        log("agent", f"Turn {turn + 1}, {len(context['messages'])} items (~{estimated['safe']} tokens)")

        payload: dict = {
            "model": model,
            "instructions": context["system_prompt"],
            "input": context["messages"],
            "store": False,
        }
        if responses_tools:
            payload["tools"] = responses_tools

        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        actual_tokens = track_usage(data.get("usage"), cal, estimated["safe"], totals)
        if actual_tokens is not None:
            log("agent", f"API usage — estimated: {estimated['safe']}, actual: {actual_tokens}")

        pending_calls = _apply_response_output(session, data.get("output", []))

        if not pending_calls:
            # Accumulate text from ALL message output items (mirrors JS output_text shortcut)
            output_text = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    output_text += get_response_message_text(item) or ""
            log("agent", f"Done ({turn + 1} turns)")
            return {"response": output_text, "usage": _build_usage(turn + 1)}

        for call in pending_calls:
            await _execute_tool_call(session, call)

    return {"response": "Exceeded maximum turns", "usage": _build_usage(AGENT_MAX_TURNS)}
