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
from pathlib import Path
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters, stdio_client

from ..helpers import logger as log

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # 02_02_hybrid_rag/


async def _load_mcp_config() -> Dict[str, Any]:
    """Read and parse the ``mcp.json`` server configuration file."""
    config_path = _PROJECT_ROOT / "mcp.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


async def create_mcp_client(server_name: str = "files") -> ClientSession:
    """Create and connect an MCP client for the named server.

    Args:
        server_name: Key in ``mcp.json`` ``mcpServers`` dict.

    Returns:
        Connected :class:`mcp.ClientSession`.

    Raises:
        KeyError: If *server_name* is not found in ``mcp.json``.
    """
    config = await _load_mcp_config()
    server_config = config["mcpServers"].get(server_name)

    if not server_config:
        raise KeyError(f'MCP server "{server_name}" not found in mcp.json')

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {server_config['command']} {' '.join(server_config['args'])}")

    transport = stdio_client(
        StdioServerParameters(
            command=server_config["command"],
            args=server_config["args"],
            env=server_config.get("env"),
        )
    )

    client = ClientSession(transport)
    await client.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return client


async def list_mcp_tools(client: ClientSession) -> List[Any]:
    """List all tools available on the connected MCP server."""
    result = await client.list_tools()
    return result.tools


async def call_mcp_tool(client: ClientSession, name: str, args: Dict[str, Any]) -> Any:
    """Call a tool on the MCP server and return its result.

    Attempts to parse text content as JSON; falls back to the raw string.

    Args:
        client: Connected MCP session.
        name: Tool name.
        args: Tool arguments.

    Returns:
        Parsed JSON or raw text from the tool response.
    """
    result = await client.call_tool(name, args)

    for content in result.content:
        if content.type == "text":
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text

    return result


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
