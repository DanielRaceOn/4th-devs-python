# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP (Model Context Protocol) client for connecting to file system server.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      mcp/client.js

"""

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

try:
    from mcp import StdioServerParameters, stdio_client, ClientSession
except ImportError:
    raise ImportError("MCP SDK not installed. Install with: pip install mcp")

from ..helpers.logger import log

PROJECT_ROOT = Path(__file__).parent.parent.parent


class McpSession:
    """Wraps a ClientSession together with its lifecycle stack."""

    def __init__(self, session: ClientSession, stack: AsyncExitStack) -> None:
        self._session = session
        self._stack = stack

    async def list_tools(self):
        """Proxy to ``ClientSession.list_tools``."""
        return await self._session.list_tools()

    async def call_tool(self, name: str, arguments: dict):
        """Proxy to ``ClientSession.call_tool``."""
        return await self._session.call_tool(name, arguments=arguments)

    async def close(self) -> None:
        """Close all managed context managers (subprocess + session)."""
        await self._stack.aclose()


async def load_mcp_config() -> dict:
    """Load MCP server configuration from mcp.json."""
    config_path = PROJECT_ROOT / "mcp.json"
    with open(config_path) as f:
        return json.load(f)


async def create_mcp_client(server_name: str = "files") -> McpSession:
    """Create and initialise an MCP client for a named server.

    Args:
        server_name: Key in ``mcp.json`` mcpServers dict.

    Returns:
        ``McpSession`` wrapping the connected ``ClientSession``.
    """
    config = await load_mcp_config()
    server_config = config["mcpServers"].get(server_name)

    if not server_config:
        raise Exception(f'MCP server "{server_name}" not found in mcp.json')

    # Use the current venv Python if the config says "python"/"python3"
    command = server_config["command"]
    if command in ("python", "python3"):
        command = sys.executable

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {command} {' '.join(server_config['args'])}")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "NODE_ENV": os.environ.get("NODE_ENV", "production"),
        **(server_config.get("env") or {}),
    }

    params = StdioServerParameters(
        command=command,
        args=server_config["args"],
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    stack = AsyncExitStack()
    await stack.__aenter__()
    read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return McpSession(session, stack)


async def list_mcp_tools(client: McpSession) -> list:
    """List all tools available on the connected MCP server."""
    response = await client.list_tools()
    return response.tools


async def call_mcp_tool(client: McpSession, name: str, args: dict) -> Any:
    """
    Call a tool on the MCP server.

    Args:
        client: Connected MCP client
        name: Tool name
        args: Tool arguments

    Returns:
        Tool result (parsed JSON if possible, otherwise string)
    """
    result = await client.call_tool(name, arguments=args)

    for content in result.content:
        if content.type == "text":
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text

    return None


def mcp_tools_to_openai(mcp_tools: list) -> list:
    """Convert MCP tool definitions to OpenAI function-calling format."""
    openai_tools = []
    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
        }
        if hasattr(tool, "inputSchema") and tool.inputSchema:
            openai_tool["parameters"] = tool.inputSchema
        else:
            openai_tool["parameters"] = {"type": "object", "properties": {}}
        openai_tools.append(openai_tool)
    return openai_tools
