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
from pathlib import Path
from typing import Any

try:
    from mcp import StdioServerParameters, stdio_client, ClientSession
except ImportError:
    raise ImportError("MCP SDK not installed. Install with: pip install mcp")

from ..helpers.logger import log

PROJECT_ROOT = Path(__file__).parent.parent.parent


async def load_mcp_config() -> dict:
    """Load MCP server configuration from mcp.json."""
    config_path = PROJECT_ROOT / "mcp.json"
    with open(config_path) as f:
        return json.load(f)


async def create_mcp_client(server_name: str = "files"):
    """
    Create an MCP client for a specific server.

    Args:
        server_name: Name of the server in mcp.json

    Returns:
        Connected MCP client
    """
    config = await load_mcp_config()
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

    transport = stdio_client(
        StdioServerParameters(
            command=server_config["command"],
            args=server_config["args"],
            env=env,
        )
    )

    client = ClientSession(transport)
    await client.initialize()
    log.success(f"Connected to {server_name} via stdio")
    return client


async def list_mcp_tools(client) -> list:
    """List all tools available on the MCP server."""
    response = await client.list_tools()
    return response.tools


async def call_mcp_tool(client, name: str, args: dict) -> Any:
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
