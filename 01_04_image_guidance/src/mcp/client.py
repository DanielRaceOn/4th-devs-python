# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP client factory — spawns a local stdio MCP server subprocess and returns a
session wrapper with list_tools / call_tool / close interface.

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

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..helpers.logger import log

# Module root: src/mcp/ → src/ → 01_04_image_guidance/
_PROJECT_ROOT = Path(__file__).parent.parent.parent


class McpSession:
    """Thin wrapper around a connected MCP ``ClientSession``.

    Keeps the ``AsyncExitStack`` alive so the underlying subprocess and
    transport are not torn down until ``close()`` is called.
    """

    def __init__(self, session: ClientSession, stack: AsyncExitStack) -> None:
        self._session = session
        self._stack = stack

    async def list_tools(self) -> list:
        """Return all tools exposed by the MCP server."""
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, args: dict) -> Any:
        """Call a named MCP tool and return its result payload.

        Args:
            name: Tool name as registered on the server.
            args: Arguments to pass to the tool.

        Returns:
            Parsed JSON dict if the text content is JSON, otherwise raw text.
        """
        result = await self._session.call_tool(name, args)
        text_content = next((c for c in result.content if c.type == "text"), None)
        if text_content:
            try:
                return json.loads(text_content.text)
            except (json.JSONDecodeError, ValueError):
                return text_content.text
        return result

    async def close(self) -> None:
        """Shut down the MCP session and subprocess."""
        await self._stack.aclose()


async def create_mcp_client(server_name: str = "files") -> McpSession:
    """Spawn an MCP server subprocess and return a connected ``McpSession``.

    Reads server configuration from ``mcp.json`` in the module root.

    Args:
        server_name: Key in the ``mcpServers`` section of ``mcp.json``.

    Returns:
        A live ``McpSession`` instance.

    Raises:
        ValueError: If ``server_name`` is not found in ``mcp.json``.
    """
    config_path = _PROJECT_ROOT / "mcp.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    server_config = config.get("mcpServers", {}).get(server_name)

    if not server_config:
        raise ValueError(f'MCP server "{server_name}" not found in mcp.json')

    # Use the current venv Python if the config says "python"/"python3"
    command = server_config["command"]
    if command in ("python", "python3"):
        command = sys.executable

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {command} {' '.join(server_config['args'])}")

    env = {
        **os.environ,
        **server_config.get("env", {}),
    }

    params = StdioServerParameters(
        command=command,
        args=server_config["args"],
        env=env,
        cwd=str(_PROJECT_ROOT),
    )

    stack = AsyncExitStack()
    read_stream, write_stream = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
    await session.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return McpSession(session, stack)


async def list_mcp_tools(client: McpSession) -> list:
    """Return the tool list from the MCP server.

    Args:
        client: Connected ``McpSession``.

    Returns:
        List of MCP tool objects.
    """
    return await client.list_tools()


async def call_mcp_tool(client: McpSession, name: str, args: dict) -> Any:
    """Call a named tool on the MCP server.

    Args:
        client: Connected ``McpSession``.
        name: Tool name.
        args: Arguments dict.

    Returns:
        Tool result (parsed JSON or raw text).
    """
    return await client.call_tool(name, args)


def mcp_tools_to_openai(mcp_tools: list) -> list:
    """Convert MCP tool definitions to OpenAI function format.

    Args:
        mcp_tools: List of MCP tool objects (from ``list_tools``).

    Returns:
        List of tool dicts in the OpenAI ``function`` format.
    """
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema,
            "strict": False,
        }
        for tool in mcp_tools
    ]
