# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP (Model Context Protocol) client lifecycle manager for the agentic RAG
module. Reads server config from mcp.json, spawns the MCP server subprocess
via stdio transport, and bridges its tools to the OpenAI function-calling
format consumed by the agent loop.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/mcp/client.js

"""

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    raise ImportError("MCP SDK not installed. Install with: pip install mcp")

from ..helpers.logger import log

# Project root is 02_01_agentic_rag/ — mcp.json lives here
PROJECT_ROOT = Path(__file__).parent.parent.parent


async def create_mcp_client(
    server_name: str = "files",
) -> tuple[ClientSession, AsyncExitStack]:
    """Spawn an MCP server subprocess and return a connected client session.

    Uses an ``AsyncExitStack`` to keep the stdio transport and session context
    managers alive for the full application lifetime. Call
    ``await exit_stack.aclose()`` (or ``await close_mcp_client()``) to
    cleanly shut down both.

    Args:
        server_name: Key in ``mcp.json`` ``mcpServers`` dict to launch.

    Returns:
        Tuple of ``(ClientSession, AsyncExitStack)`` — both must be retained
        until shutdown.

    Raises:
        KeyError: If ``server_name`` is not found in ``mcp.json``.
        FileNotFoundError: If ``mcp.json`` does not exist.
    """
    config_path = PROJECT_ROOT / "mcp.json"
    with open(config_path) as f:
        config = json.load(f)

    server_config = config["mcpServers"].get(server_name)
    if not server_config:
        raise KeyError(f'MCP server "{server_name}" not found in mcp.json')

    # Use the current venv Python if the config says "python"/"python3"
    command = server_config["command"]
    if command in ("python", "python3"):
        command = sys.executable

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {command} {' '.join(server_config['args'])}")

    # Pass through essential env vars plus any server-specific overrides
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "NODE_ENV": os.environ.get("NODE_ENV", "production"),
        **(server_config.get("env") or {}),
    }

    server_params = StdioServerParameters(
        command=command,
        args=server_config["args"],
        env=env,
        # Set cwd so the MCP server resolves FS_ROOT="." relative to the
        # project root, regardless of where the user launched app.py from
        cwd=str(PROJECT_ROOT),
    )

    # Use AsyncExitStack so both context managers stay open for the session
    exit_stack = AsyncExitStack()
    read, write = await exit_stack.enter_async_context(stdio_client(server_params))
    session = await exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    log.success(f"Connected to MCP server: {server_name}")
    return session, exit_stack


async def list_mcp_tools(client: ClientSession) -> list:
    """Discover all tools exposed by the connected MCP server.

    Args:
        client: Connected ``ClientSession``.

    Returns:
        List of MCP tool definition objects.
    """
    response = await client.list_tools()
    return response.tools


async def call_mcp_tool(
    client: ClientSession, name: str, args: dict
) -> Any:
    """Invoke a named tool on the MCP server and return its result.

    Finds the first ``text``-type content item in the result and attempts
    ``json.loads``; falls back to the raw string if parsing fails. This
    mirrors the JS behaviour and lets the agent receive structured data when
    the server returns JSON.

    Args:
        client: Connected ``ClientSession``.
        name: Tool name to invoke.
        args: Arguments dict to pass to the tool.

    Returns:
        Parsed JSON value, raw string, or ``None`` if no text content found.
    """
    result = await client.call_tool(name, arguments=args)
    for content in result.content:
        if content.type == "text":
            try:
                return json.loads(content.text)
            except (json.JSONDecodeError, ValueError):
                return content.text
    return None


async def close_mcp_client(exit_stack: AsyncExitStack) -> None:
    """Cleanly close the MCP session and transport.

    Args:
        exit_stack: The ``AsyncExitStack`` returned by ``create_mcp_client``.
    """
    try:
        await exit_stack.aclose()
    except Exception as exc:
        log.warn(f"Error closing MCP client: {exc}")


def mcp_tools_to_openai(mcp_tools: list) -> list:
    """Convert MCP tool definitions to OpenAI function-calling format.

    The OpenAI Responses API expects tools shaped as::

        {
            "type": "function",
            "name": "<name>",
            "description": "<desc>",
            "parameters": { ... JSON Schema ... },
            "strict": False,
        }

    Args:
        mcp_tools: List of MCP tool definition objects from ``list_tools()``.

    Returns:
        List of tool dicts ready to pass to the Responses API.
    """
    openai_tools = []
    for tool in mcp_tools:
        entry: dict[str, Any] = {
            "type": "function",
            "name": tool.name,
            "description": tool.description or "",
            "strict": False,
        }
        if hasattr(tool, "inputSchema") and tool.inputSchema:
            entry["parameters"] = tool.inputSchema
        else:
            entry["parameters"] = {"type": "object", "properties": {}}
        openai_tools.append(entry)
    return openai_tools
