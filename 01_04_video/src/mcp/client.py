# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP stdio client for the video processing agent. Wraps the Python ``mcp`` SDK
(v1.26.0) to spawn the ``files-mcp`` TypeScript server via ``npx tsx`` and expose
list_mcp_tools / call_mcp_tool / mcp_tools_to_openai helpers.

Key difference from the JS version: the Python MCP client uses async context
managers (``stdio_client`` + ``ClientSession``). Use ``create_mcp_client()`` as
an ``async with`` block — the stdio subprocess stays alive for the block's lifetime.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/mcp/client.js`


"""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..helpers.logger import log

logger = logging.getLogger(__name__)

# Module root is 01_04_video/  (two dirs up from src/mcp/)
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent


def _load_mcp_config() -> dict[str, Any]:
    """Load MCP server configuration from ``mcp.json`` at the project root.

    Returns:
        Parsed JSON dict from ``mcp.json``.

    Raises:
        FileNotFoundError: When ``mcp.json`` does not exist.
    """
    config_path = PROJECT_ROOT / "mcp.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


@asynccontextmanager
async def create_mcp_client(
    server_name: str = "files",
) -> AsyncGenerator[ClientSession, None]:
    """Async context manager that spawns an MCP server and yields a ready session.

    Reads server command and args from ``mcp.json``, spawns the child process via
    stdio, initialises the session, and yields it. The subprocess lives for the
    duration of the ``async with`` block.

    Args:
        server_name: Key inside ``mcpServers`` in ``mcp.json``; default ``"files"``.

    Yields:
        Initialised :class:`mcp.ClientSession`.

    Raises:
        RuntimeError: When ``server_name`` is not found in ``mcp.json``.
    """
    config = _load_mcp_config()
    server_cfg = config.get("mcpServers", {}).get(server_name)
    if not server_cfg:
        raise RuntimeError(f'MCP server "{server_name}" not found in mcp.json')

    log.info(f"Spawning MCP server: {server_name}")
    log.info(f"Command: {server_cfg['command']} {' '.join(server_cfg.get('args', []))}")

    params = StdioServerParameters(
        command=server_cfg["command"],
        args=server_cfg.get("args", []),
        env=server_cfg.get("env"),  # merged with default inherited env by the SDK
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            log.success(f"Connected to {server_name} via stdio")
            yield session


async def list_mcp_tools(session: ClientSession) -> list[Any]:
    """List all tools available on the MCP server.

    Args:
        session: Initialised MCP client session.

    Returns:
        List of MCP Tool objects (each with ``.name``, ``.description``,
        ``.inputSchema``).
    """
    result = await session.list_tools()
    return result.tools


async def call_mcp_tool(session: ClientSession, name: str, args: dict[str, Any]) -> Any:
    """Call a tool on the MCP server and return its result.

    Extracts the first ``text`` content item from the result. Tries to JSON-parse
    it; falls back to returning the raw string.

    Args:
        session: Initialised MCP client session.
        name: Tool name to call.
        args: Arguments dict to pass to the tool.

    Returns:
        Parsed JSON object, raw string, or the full result object when no text
        content is present.
    """
    result = await session.call_tool(name, arguments=args)

    text_item = next((c for c in result.content if c.type == "text"), None)
    if text_item:
        try:
            return json.loads(text_item.text)
        except (json.JSONDecodeError, ValueError):
            return text_item.text

    return result


def mcp_tools_to_openai(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI Responses API function format.

    Args:
        mcp_tools: List of MCP Tool objects from ``list_mcp_tools()``.

    Returns:
        List of OpenAI function tool dicts (type, name, description, parameters,
        strict).
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
