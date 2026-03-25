# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Recursive multi-turn agent loop. Loads agent templates from workspace/agents/,
executes tool calls (including sub-agent delegation via the ``delegate`` tool),
and returns the final text response.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      src/agent.ts


"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from .config import (
    AI_API_KEY,
    CHAT_COMPLETIONS_ENDPOINT,
    EXTRA_API_HEADERS,
    resolve_model_for_provider,
)
from .tools import find_tool, tools

logger = logging.getLogger(__name__)

MAX_DEPTH: int = 3
MAX_TURNS: int = 15

WORKSPACE: Path = Path(__file__).parent.parent / "workspace"


def _truncate(text: str, max_len: int = 100) -> str:
    """Truncate a string for readable log output.

    Args:
        text: Input string.
        max_len: Maximum allowed length before truncation.

    Returns:
        Original string or truncated string ending with ``…``.
    """
    return text[:max_len] + "…" if len(text) > max_len else text


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Replaces the ``gray-matter`` npm dependency. Expects::

        ---
        key: value
        ---
        body text

    The closing ``---`` must appear on its own line (followed by ``\\n`` or
    end of string), preventing false matches inside YAML values. Body stripping
    handles both LF and CRLF line endings (Windows-safe).

    Args:
        raw: Full file content including optional frontmatter.

    Returns:
        Tuple of (frontmatter dict, body string). Returns empty dict and the
        full text when no ``---`` delimiters are found.
    """
    raw = raw.lstrip()
    if not raw.startswith("---"):
        return {}, raw

    # Require closing --- to be on its own line (newline or EOF after dashes)
    match = re.search(r"\n---[ \t]*(\r?\n|$)", raw[3:])
    if not match:
        return {}, raw

    yaml_block = raw[3: match.start() + 3].strip()
    body = raw[3 + match.end():].lstrip("\r\n")

    try:
        data = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        data = {}

    return data, body


@dataclass
class AgentTemplate:
    """Parsed agent definition from a ``.agent.md`` file.

    Attributes:
        name: Agent identifier.
        model: Raw model string from frontmatter (``openai:`` prefix stripped).
        tools: List of tool names the agent is permitted to call.
        system_prompt: Markdown body used as the system message.
    """

    name: str
    model: str
    tools: list[str] = field(default_factory=list)
    system_prompt: str = ""


def _load_agent(name: str) -> AgentTemplate:
    """Load and parse an agent template from ``workspace/agents/``.

    Args:
        name: Agent name without extension (e.g. ``orchestrator``).

    Returns:
        Parsed :class:`AgentTemplate`.

    Raises:
        FileNotFoundError: When the ``.agent.md`` file does not exist.
    """
    file_path = WORKSPACE / "agents" / f"{name}.agent.md"
    raw = file_path.read_text(encoding="utf-8")
    data, body = _parse_frontmatter(raw)

    # Strip the ``openai:`` vendor prefix the JS config uses in frontmatter
    raw_model: str = str(data.get("model", "gpt-4.1-mini"))
    if raw_model.startswith("openai:"):
        raw_model = raw_model[len("openai:"):]

    tool_list = data.get("tools", [])
    if not isinstance(tool_list, list):
        tool_list = []

    return AgentTemplate(
        name=str(data.get("name", name)),
        model=raw_model,
        tools=[str(t) for t in tool_list],
        system_prompt=body.strip(),
    )


async def run_agent(
    agent_name: str,
    task: str,
    depth: int = 0,
) -> str:
    """Run a named agent on a task, executing tool calls recursively.

    Mirrors the JS ``runAgent`` function in ``src/agent.ts``. The agent loop
    runs up to ``MAX_TURNS`` chat turns. When the LLM emits a ``delegate``
    tool call, the loop recursively calls ``run_agent`` with ``depth + 1``
    instead of dispatching to the tool handler.

    Args:
        agent_name: Name of the agent to load from ``workspace/agents/``.
        task: Task description passed as the first user message.
        depth: Current recursion depth for sub-agent delegation.

    Returns:
        Final text response from the agent, or an error string on failure.
    """
    if depth > MAX_DEPTH:
        return "Max agent depth exceeded"

    logger.info("[%s] Starting (depth=%d)", agent_name, depth)

    try:
        template = _load_agent(agent_name)
    except FileNotFoundError as exc:
        logger.error("[%s] Agent file not found: %s", agent_name, exc)
        return f"Agent error: {exc}"

    model = resolve_model_for_provider(template.model)

    # Build the list of OpenAI-format tool definitions for this agent
    agent_tool_defs: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": t.definition["name"],
                "description": t.definition["description"],
                "parameters": t.definition["parameters"],
            },
        }
        for t in tools
        if t.definition["name"] in template.tools
    ]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": template.system_prompt},
        {"role": "user", "content": task},
    ]

    headers: dict[str, str] = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        **EXTRA_API_HEADERS,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            for turn in range(MAX_TURNS):
                payload: dict[str, Any] = {"model": model, "messages": messages}
                if agent_tool_defs:
                    payload["tools"] = agent_tool_defs

                response = await client.post(
                    CHAT_COMPLETIONS_ENDPOINT,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                choice = data.get("choices", [{}])[0]
                message = choice.get("message")
                if not message:
                    return "Agent error: No response from model"

                tool_calls = message.get("tool_calls")

                # No tool calls → final answer; append and return immediately
                if not tool_calls:
                    messages.append({"role": "assistant", "content": message.get("content")})
                    logger.info("[%s] Completed in %d turn(s)", agent_name, turn + 1)
                    content = message.get("content") or ""
                    return content if isinstance(content, str) else str(content)

                # Append the assistant turn (with tool_calls) to conversation history
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content"),
                        "tool_calls": tool_calls,
                    }
                )

                # Execute each tool call and collect results
                for tool_call in tool_calls:
                    if tool_call.get("type") != "function":
                        continue

                    fn = tool_call.get("function", {})
                    name: str = fn.get("name", "")
                    raw_args: str = fn.get("arguments", "{}")

                    try:
                        args: dict[str, Any] = (
                            json.loads(raw_args) if raw_args.strip() else {}
                        )
                    except json.JSONDecodeError:
                        args = {}

                    logger.debug(
                        "[%s] Tool call: %s(%s)",
                        agent_name,
                        name,
                        _truncate(json.dumps(args)),
                    )

                    # ``delegate`` is handled here, not by the tool handler,
                    # so the sub-agent gets its own full conversation context.
                    if name == "delegate":
                        sub_agent = args.get("agent", "")
                        delegated_task = args.get("task", "")
                        if not isinstance(sub_agent, str):
                            sub_agent = str(sub_agent)
                        if not isinstance(delegated_task, str):
                            delegated_task = str(delegated_task)
                        logger.info(
                            "[%s] → delegating to [%s]: %s",
                            agent_name,
                            sub_agent,
                            _truncate(delegated_task),
                        )
                        result = await run_agent(sub_agent, delegated_task, depth + 1)
                    else:
                        tool = find_tool(name)
                        result = await tool.handler(args) if tool else f"Unknown tool: {name}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "content": result,
                        }
                    )

        return "Agent exceeded maximum turns without a final response"

    except httpx.HTTPStatusError as exc:
        msg = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        logger.error("[%s] HTTP error: %s", agent_name, msg)
        return f"Agent error: {msg}"
    except Exception as exc:
        logger.error("[%s] Unexpected error: %s", agent_name, exc)
        return f"Agent error: {exc}"
