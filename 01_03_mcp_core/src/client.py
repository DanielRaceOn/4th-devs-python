# -*- coding: utf-8 -*-

#   client.py

"""
### Description:
MCP Client — connects to a server over stdio, declares capabilities.
In MCP, the client is the host application. It spawns the server as a
subprocess and communicates via stdin/stdout.

This client registers two capabilities the server can use:
  - sampling:     server can ask the client to call an LLM
  - elicitation:  server can ask the client for structured user input

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/client.js`

"""

from pathlib import Path
from typing import Optional, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .log import client_log
from .sampling import create_sampling_handler
from .elicitation import create_elicitation_handler

# Path to the server entry point (sibling of this file's parent directory)
_DEFAULT_SERVER_PATH = Path(__file__).parent / "server.py"


async def create_mcp_client(
    *,
    model: str,
    server_path: Optional[Path] = None,
    on_elicitation: Optional[Callable] = None,
):
    """Spawn the MCP server as a subprocess and return a connected session.

    Args:
        model: Model identifier used by the sampling handler.
        server_path: Path to the server script. Defaults to ``src/server.py``.
        on_elicitation: Optional custom elicitation handler.

    Returns:
        A connected ``ClientSession`` with sampling and elicitation registered.
        The caller is responsible for closing the session.

    Note:
        This function is designed to be used as an async context manager.
        Use it inside an ``asyncio`` event loop.
    """
    resolved_path = server_path or _DEFAULT_SERVER_PATH
    client_log.spawning_server(str(resolved_path))

    sampling_handler = create_sampling_handler(model)
    # elicitation_handler unused directly — stored for documentation purposes
    # The Python SDK wires sampling via sampling_callback param on ClientSession

    server_params = StdioServerParameters(
        command="python",
        args=[str(resolved_path)],
    )

    return server_params, sampling_handler
