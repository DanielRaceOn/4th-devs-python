# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
MCP server configuration — loads and validates mcp.json.
Supports two transport types:
  - stdio: spawns a local process (e.g. files-mcp)
  - http:  connects to a remote StreamableHTTP endpoint (e.g. uploadthing)

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/mcp/config.js`

"""

import json
from pathlib import Path
from urllib.parse import urlparse

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MCP_CONFIG_PATH = _PROJECT_ROOT / "mcp.json"
_UPLOADTHING_PLACEHOLDER = "https://URL_TO_YOUR_MCP_SERVER/mcp"

PROJECT_ROOT = _PROJECT_ROOT


class ConfigurationError(Exception):
    """Raised when mcp.json is missing or contains invalid configuration."""


def validate_http_server_config(server_name: str, server_config: dict) -> None:
    """Validate an HTTP server entry in mcp.json.

    Args:
        server_name: Key used in the ``mcpServers`` object.
        server_config: The server config dict.

    Raises:
        ConfigurationError: If the URL is missing, is a placeholder, or invalid.
    """
    url = (server_config.get("url") or "").strip()
    config_path = "mcp.json"

    if not url:
        raise ConfigurationError(
            f"Invalid {config_path}: set mcpServers.{server_name}.url to the deployed "
            f"MCP endpoint from the AI_devs lesson, e.g. https://your-domain.example/mcp"
        )

    if url == _UPLOADTHING_PLACEHOLDER or "URL_TO_YOUR_MCP_SERVER" in url:
        raise ConfigurationError(
            f"Invalid {config_path}: replace the mcpServers.{server_name}.url placeholder "
            f"with the deployed MCP endpoint from the AI_devs lesson, "
            f"e.g. https://your-domain.example/mcp"
        )

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError
    except ValueError:
        raise ConfigurationError(
            f"Invalid {config_path}: mcpServers.{server_name}.url must be a full "
            f"http(s) URL, e.g. https://your-domain.example/mcp"
        )


def validate_mcp_config(config: dict) -> None:
    """Validate the full mcp.json config structure.

    Args:
        config: Parsed mcp.json dict.

    Raises:
        ConfigurationError: If the structure is invalid or HTTP servers misconfigured.
    """
    if not isinstance(config.get("mcpServers"), dict):
        raise ConfigurationError(
            'Invalid mcp.json: expected a top-level "mcpServers" object'
        )

    for server_name, server_config in config["mcpServers"].items():
        transport = (server_config.get("transport") or "stdio")
        if transport == "http":
            validate_http_server_config(server_name, server_config)


def load_mcp_config() -> dict:
    """Load and parse mcp.json from the module root.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If mcp.json does not exist.
    """
    if not _MCP_CONFIG_PATH.exists():
        raise FileNotFoundError(f"mcp.json not found at {_MCP_CONFIG_PATH}")
    return json.loads(_MCP_CONFIG_PATH.read_text(encoding="utf-8"))
