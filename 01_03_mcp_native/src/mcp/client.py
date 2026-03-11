# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP client — connects to a server via in-memory transport.
In-memory transport is used here because the server runs in the same
process (unlike mcp_core which uses stdio for a subprocess).
Wrapper functions bridge MCP tool format to OpenAI function format
so the agent can treat MCP tools like any other tool.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/mcp/client.js`

"""

import json
from typing import Any

from mcp import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session


async def create_mcp_client(server: FastMCP) -> ClientSession:
    """Create a ClientSession connected to an in-memory FastMCP server.

    Args:
        server: The ``FastMCP`` server instance to connect to.

    Returns:
        An initialized ``ClientSession`` connected via in-memory transport.

    Note:
        The caller must manage the session lifecycle. Use this inside an
        ``asyncio`` run block and close the session when done.
    """
    # FastMCP exposes the underlying Server as ._mcp_server
    session = await create_connected_server_and_client_session(server._mcp_server)
    return session


async def list_mcp_tools(client: ClientSession) -> list[Any]:
    """List all tools available on the connected MCP server.

    Args:
        client: An initialized ``ClientSession``.

    Returns:
        List of tool objects.
    """
    result = await client.list_tools()
    return result.tools


async def call_mcp_tool(client: ClientSession, name: str, args: dict) -> Any:
    """Call a tool on the MCP server and parse the text result as JSON.

    Args:
        client: An initialized ``ClientSession``.
        name: Tool name.
        args: Tool arguments.

    Returns:
        Parsed JSON value, or the raw result if no text content.
    """
    result = await client.call_tool(name, args)
    text_content = next(
        (c for c in result.content if c.type == "text"), None
    )
    if text_content:
        try:
            return json.loads(text_content.text)
        except json.JSONDecodeError:
            return text_content.text
    return result


def mcp_tools_to_openai(mcp_tools: list[Any]) -> list[dict]:
    """Convert MCP tool schemas to OpenAI function-calling format.

    Args:
        mcp_tools: List of MCP tool objects from ``list_tools()``.

    Returns:
        List of tool dicts in OpenAI ``{"type": "function", ...}`` format.
    """
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema,
            "strict": True,
        }
        for tool in mcp_tools
    ]
