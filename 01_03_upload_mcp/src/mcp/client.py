# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
Multi-server MCP client — connects to all servers defined in mcp.json.
Supports stdio and HTTP (StreamableHTTP) transports.
Tool names are prefixed with the server name (e.g. "files__fs_read")
so the agent can route calls back to the correct server.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/mcp/client.js`

"""

import json
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .config import (
    ConfigurationError,
    PROJECT_ROOT,
    load_mcp_config,
    validate_mcp_config,
    validate_http_server_config,
)
from ..helpers.logger import log

__all__ = [
    "ConfigurationError",
    "create_all_mcp_clients",
    "list_all_mcp_tools",
    "call_mcp_tool",
    "mcp_tools_to_openai",
    "close_all_clients",
]

# Holds open context managers for cleanup
_cm_stack: dict[str, Any] = {}


async def _create_stdio_client(server_name: str, server_config: dict) -> ClientSession:
    """Spawn a subprocess MCP server and return a connected session."""
    cmd = server_config["command"]
    args = server_config.get("args", [])
    log.info(f"Spawning stdio server: {cmd} {' '.join(args)}")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "NODE_ENV": os.environ.get("NODE_ENV", ""),
        **(server_config.get("env") or {}),
    }

    params = StdioServerParameters(
        command=cmd,
        args=args,
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    cm = stdio_client(params)
    read, write = await cm.__aenter__()
    _cm_stack[server_name + "_transport"] = cm

    session = ClientSession(read, write)
    await session.__aenter__()
    return session


async def _create_http_client(server_name: str, server_config: dict) -> ClientSession:
    """Connect to a remote StreamableHTTP MCP server and return a session."""
    validate_http_server_config(server_name, server_config)
    url = server_config["url"]
    log.info(f"Connecting to HTTP server: {url}")

    cm = streamablehttp_client(url)
    read, write, _ = await cm.__aenter__()
    _cm_stack[server_name + "_transport"] = cm

    session = ClientSession(read, write)
    await session.__aenter__()
    return session


async def create_all_mcp_clients() -> dict[str, ClientSession]:
    """Connect to all MCP servers defined in mcp.json.

    Returns:
        Dict mapping server names to initialized ``ClientSession`` objects.

    Raises:
        ConfigurationError: If mcp.json is invalid.
    """
    config = load_mcp_config()
    validate_mcp_config(config)

    clients: dict[str, ClientSession] = {}

    try:
        for server_name, server_config in config["mcpServers"].items():
            transport = (server_config.get("transport") or "stdio")
            if transport == "http":
                client = await _create_http_client(server_name, server_config)
            else:
                client = await _create_stdio_client(server_name, server_config)

            await client.initialize()
            log.success(f"Connected to {server_name} via {transport}")
            clients[server_name] = client

    except Exception:
        await close_all_clients(clients)
        raise

    return clients


async def list_all_mcp_tools(clients: dict[str, ClientSession]) -> list[Any]:
    """List all tools from all servers, prefixing names with the server name.

    Tool names are prefixed so the agent can route calls back:
    ``"files__fs_read"``, ``"uploadthing__upload_files"``, etc.

    Args:
        clients: Dict of server name → session.

    Returns:
        Flat list of tool objects with ``name`` prefixed and ``_server`` metadata.
    """
    all_tools: list[Any] = []

    for server_name, client in clients.items():
        try:
            result = await client.list_tools()
            tools = result.tools
        except Exception as error:
            # Some servers return non-standard outputSchema; fall back gracefully
            if "outputSchema" in str(error) or "ZodError" in str(error):
                log.warn(f"Tool listing validation failed for {server_name}, using raw request")
                raw = await client.send_request({"method": "tools/list", "params": {}})
                tools = raw.get("tools", [])
            else:
                raise

        tool_names = [t.name if hasattr(t, "name") else t.get("name", "?") for t in tools]
        log.info(f"  {server_name}: {', '.join(tool_names)}")

        for tool in tools:
            # Attach prefixed name and server metadata while preserving original schema
            prefixed = type("PrefixedTool", (), {
                "name": f"{server_name}__{getattr(tool, 'name', tool.get('name'))}",
                "description": getattr(tool, "description", tool.get("description", "")),
                "inputSchema": getattr(tool, "inputSchema", tool.get("inputSchema", {})),
                "_server": server_name,
                "_original_name": getattr(tool, "name", tool.get("name")),
            })()
            all_tools.append(prefixed)

    return all_tools


async def call_mcp_tool(clients: dict[str, ClientSession], name: str, args: dict) -> Any:
    """Route a prefixed tool call to the correct server.

    Args:
        clients: Dict of server name → session.
        name: Prefixed tool name, e.g. ``"files__fs_read"``.
        args: Tool arguments.

    Returns:
        Parsed JSON result, or raw text.

    Raises:
        ValueError: If the server part of the name is not in ``clients``.
    """
    server_name, _, tool_name = name.partition("__")
    client = clients.get(server_name)

    if not client:
        raise ValueError(f"Unknown MCP server: {server_name}")

    result = await client.call_tool(tool_name, args)

    text_content = next((c for c in result.content if c.type == "text"), None)
    if text_content:
        try:
            return json.loads(text_content.text)
        except json.JSONDecodeError:
            return text_content.text
    return result


def mcp_tools_to_openai(mcp_tools: list[Any]) -> list[dict]:
    """Convert prefixed MCP tools to OpenAI function-calling format.

    Args:
        mcp_tools: Tool objects returned by ``list_all_mcp_tools()``.

    Returns:
        List of OpenAI tool dicts with prefixed names.
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


async def close_all_clients(clients: dict[str, ClientSession]) -> None:
    """Close all open MCP sessions and their underlying transports.

    Args:
        clients: Dict of server name → session.
    """
    for name, client in clients.items():
        try:
            await client.__aexit__(None, None, None)
            log.info(f"Closed {name} client")
        except Exception as e:
            log.warn(f"Error closing {name}: {e}")

        # Also tear down the underlying transport context manager
        cm = _cm_stack.pop(name + "_transport", None)
        if cm:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass
