# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP client — connects to an external server via stdio transport.
Reads server configuration from mcp.json in the module root and spawns
the configured process. Bridges MCP tool format to OpenAI function format.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/mcp/client.js`

"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.helpers.logger import log

# Module root is two levels up from this file
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MCP_CONFIG_PATH = _PROJECT_ROOT / "mcp.json"


def _load_mcp_config() -> dict:
    """Load and parse mcp.json from the module root.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If mcp.json is not found.
    """
    if not _MCP_CONFIG_PATH.exists():
        raise FileNotFoundError(f"mcp.json not found at {_MCP_CONFIG_PATH}")
    return json.loads(_MCP_CONFIG_PATH.read_text(encoding="utf-8"))


async def create_mcp_client(server_name: str = "files") -> ClientSession:
    """Create an MCP client for a server defined in mcp.json.

    Args:
        server_name: Key in the ``mcpServers`` object of mcp.json.

    Returns:
        An initialized ``ClientSession`` connected via stdio.

    Raises:
        KeyError: If the server name is not found in mcp.json.
    """
    config = _load_mcp_config()
    server_cfg = config["mcpServers"].get(server_name)

    if not server_cfg:
        raise KeyError(f'MCP server "{server_name}" not found in mcp.json')

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {server_cfg['command']} {' '.join(server_cfg.get('args', []))}")

    # Merge environment: inherit PATH/HOME/NODE_ENV and any server-specific vars
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "NODE_ENV": os.environ.get("NODE_ENV", ""),
        **(server_cfg.get("env") or {}),
    }

    server_params = StdioServerParameters(
        command=server_cfg["command"],
        args=server_cfg.get("args", []),
        env=env,
        cwd=str(_PROJECT_ROOT),
    )

    # stdio_client is a context manager; we return the session for the caller to manage
    _read, _write = await stdio_client(server_params).__aenter__()
    session = ClientSession(_read, _write)
    await session.__aenter__()
    await session.initialize()

    log.success(f"Connected to {server_name} via stdio")
    return session


async def list_mcp_tools(client: ClientSession) -> list[Any]:
    """List all tools available on the MCP server.

    Args:
        client: An initialized ``ClientSession``.

    Returns:
        List of tool objects.
    """
    result = await client.list_tools()
    return result.tools


async def call_mcp_tool(client: ClientSession, name: str, args: dict) -> Any:
    """Call a tool on the MCP server and parse the text result.

    Args:
        client: An initialized ``ClientSession``.
        name: Tool name.
        args: Tool arguments.

    Returns:
        Parsed JSON value, or raw text string if not valid JSON.
    """
    result = await client.call_tool(name, args)
    text_content = next((c for c in result.content if c.type == "text"), None)
    if text_content:
        try:
            return json.loads(text_content.text)
        except json.JSONDecodeError:
            return text_content.text
    return result


def mcp_tools_to_openai(mcp_tools: list[Any]) -> list[dict]:
    """Convert MCP tool schemas to OpenAI function-calling format.

    Args:
        mcp_tools: List of MCP tool objects.

    Returns:
        List of tool dicts in OpenAI ``{"type": "function", ...}`` format.
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
