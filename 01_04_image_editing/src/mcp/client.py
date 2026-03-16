# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP (Model Context Protocol) client for connecting to the file system server.
Uses AsyncExitStack to keep stdio_client and ClientSession context managers
alive for the full lifetime of the returned session wrapper.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/mcp/client.js

"""

import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

try:
    from mcp import StdioServerParameters, stdio_client, ClientSession
except ImportError:
    raise ImportError("MCP SDK not installed. Install with: pip install mcp")

from ..helpers.logger import log

# Module root: src/mcp/ → src/ → module root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class McpSession:
    """Wraps a ClientSession together with its lifecycle stack.

    Holds an ``AsyncExitStack`` that keeps both the ``stdio_client`` subprocess
    and the ``ClientSession`` context managers alive. Call ``close()`` when done.
    """

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


async def _load_mcp_config() -> dict:
    """Load MCP server configuration from mcp.json.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If ``mcp.json`` is not found at the module root.
    """
    config_path = PROJECT_ROOT / "mcp.json"
    with open(config_path) as f:
        return json.load(f)


async def create_mcp_client(server_name: str = "files") -> McpSession:
    """Create and initialise an MCP client for a named server.

    Uses ``AsyncExitStack`` to hold ``stdio_client`` and ``ClientSession``
    context managers open for the lifetime of the returned ``McpSession``.
    Call ``McpSession.close()`` to shut down the subprocess cleanly.

    Args:
        server_name: Key in ``mcp.json`` mcpServers dict.

    Returns:
        ``McpSession`` wrapping the connected ``ClientSession``.

    Raises:
        FileNotFoundError: If ``mcp.json`` is not found at the module root.
        Exception: If the server name is not found in ``mcp.json``.
    """
    config = await _load_mcp_config()
    server_config = config["mcpServers"].get(server_name)

    if not server_config:
        raise Exception(f'MCP server "{server_name}" not found in mcp.json')

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {server_config['command']} {' '.join(server_config['args'])}")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "NODE_ENV": os.environ.get("NODE_ENV", "production"),
        **(server_config.get("env") or {}),
    }

    params = StdioServerParameters(
        command=server_config["command"],
        args=server_config["args"],
        env=env,
    )

    # AsyncExitStack keeps both the stdio subprocess and the session alive
    # until McpSession.close() is called.
    stack = AsyncExitStack()
    await stack.__aenter__()
    read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return McpSession(session, stack)


async def list_mcp_tools(client: McpSession) -> list:
    """List all tools available on the connected MCP server.

    Args:
        client: Connected ``McpSession``.

    Returns:
        List of tool definition objects.
    """
    response = await client.list_tools()
    return response.tools


async def call_mcp_tool(client: McpSession, name: str, args: dict) -> Any:
    """Call a named tool on the MCP server.

    Args:
        client: Connected ``McpSession``.
        name: Tool name to invoke.
        args: Arguments dict for the tool.

    Returns:
        Parsed JSON result if the response is valid JSON, otherwise raw text.
        ``None`` if no text content is present.
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
    """Convert MCP tool definitions to OpenAI function-calling format.

    Args:
        mcp_tools: List of MCP tool definition objects.

    Returns:
        List of tool dicts in OpenAI format.
    """
    openai_tools = []

    for tool in mcp_tools:
        openai_tool: dict = {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "strict": False,
        }

        if hasattr(tool, "inputSchema") and tool.inputSchema:
            openai_tool["parameters"] = tool.inputSchema
        else:
            openai_tool["parameters"] = {"type": "object", "properties": {}}

        openai_tools.append(openai_tool)

    return openai_tools
