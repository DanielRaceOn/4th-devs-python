# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP client for connecting to stdio-based MCP servers. Present for future
extensibility but not wired into the current agent flow.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/mcp/client.js

"""

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..helpers import logger as log

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # 02_02_hybrid_rag/


class McpSession:
    """Wraps a ClientSession together with its lifecycle stack."""

    def __init__(self, session: ClientSession, stack: AsyncExitStack) -> None:
        self._session = session
        self._stack = stack

    async def list_tools(self) -> list:
        """Return all tools exposed by the MCP server."""
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, args: dict) -> Any:
        """Call a named MCP tool and return its result payload."""
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


async def _load_mcp_config() -> Dict[str, Any]:
    """Read and parse the ``mcp.json`` server configuration file."""
    config_path = _PROJECT_ROOT / "mcp.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


async def create_mcp_client(server_name: str = "files") -> McpSession:
    """Create and connect an MCP client for the named server.

    Args:
        server_name: Key in ``mcp.json`` ``mcpServers`` dict.

    Returns:
        Connected :class:`McpSession`.

    Raises:
        KeyError: If *server_name* is not found in ``mcp.json``.
    """
    config = await _load_mcp_config()
    server_config = config["mcpServers"].get(server_name)

    if not server_config:
        raise KeyError(f'MCP server "{server_name}" not found in mcp.json')

    # Use the current venv Python if the config says "python"/"python3"
    command = server_config["command"]
    if command in ("python", "python3"):
        command = sys.executable

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {command} {' '.join(server_config['args'])}")

    params = StdioServerParameters(
        command=command,
        args=server_config["args"],
        env=server_config.get("env"),
        cwd=str(_PROJECT_ROOT),
    )

    stack = AsyncExitStack()
    read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return McpSession(session, stack)


async def list_mcp_tools(client: McpSession) -> List[Any]:
    """List all tools available on the connected MCP server."""
    return await client.list_tools()


async def call_mcp_tool(client: McpSession, name: str, args: Dict[str, Any]) -> Any:
    """Call a tool on the MCP server and return its result.

    Attempts to parse text content as JSON; falls back to the raw string.

    Args:
        client: Connected MCP session.
        name: Tool name.
        args: Tool arguments.

    Returns:
        Parsed JSON or raw text from the tool response.
    """
    return await client.call_tool(name, args)


def mcp_tools_to_openai(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function format.

    Args:
        mcp_tools: List of MCP tool objects from :func:`list_mcp_tools`.

    Returns:
        List of tool dicts in OpenAI function-call format.
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
