# -*- coding: utf-8 -*-

#   log.py

"""
### Description:
Logging and result helpers for the MCP core demo.
Provides colored terminal output and tool-result parsing utilities.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/log.js`

"""

import json
import sys
from typing import Any


# ANSI escape codes for colored terminal output
_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"
_MAGENTA = "\x1b[35m"


def _truncate(value: Any, max_length: int = 50) -> str:
    """Truncate a value to a maximum string length."""
    text = str(value)
    return text[:max_length] + "..." if len(text) > max_length else text


def _get_error_message(cause: BaseException) -> str:
    return str(cause)


def heading(title: str, description: str = "") -> None:
    """Print a bold section heading."""
    print(f"\n{_BOLD}═══ {title} ═══{_RESET}")
    if description:
        print(f"{_DIM}{description}{_RESET}")


def log(label: str, data: Any = None) -> None:
    """Print a labeled data block with colored formatting."""
    print(f"\n{_BOLD}{_CYAN}▶ {label}{_RESET}")

    if data is None:
        return

    if isinstance(data, list):
        lines = [str(item) for item in data]
    elif isinstance(data, str):
        lines = [data]
    else:
        lines = json.dumps(data, indent=2).split("\n")

    for line in lines:
        print(f"{_DIM}  {line}{_RESET}")


def parse_tool_result(result: dict) -> Any:
    """Extract and parse the text content from an MCP tool result.

    Args:
        result: MCP tool call result dict with a ``content`` list.

    Returns:
        Parsed JSON value if the text is valid JSON, otherwise raw text.

    Raises:
        RuntimeError: If the tool returned an error.
    """
    content = result.get("content") or []
    text = next((c.get("text", "") for c in content if c.get("type") == "text"), "")

    if result.get("isError"):
        raise RuntimeError(text or "Tool call failed")

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


# Structured logger for client-side events (sampling, elicitation, connection)
class _ClientLog:
    def spawning_server(self, server_path: str) -> None:
        print(f"\n{_GREEN}🚀 Spawning MCP server: {server_path}{_RESET}")

    def connected(self) -> None:
        print(f"{_GREEN}✓ Connected to MCP server via stdio{_RESET}")

    def sampling_request(self, messages: list, max_tokens: Any) -> None:
        print(f"\n{_MAGENTA}  📡 Sampling — server asked the client to call an LLM{_RESET}")
        print(f"{_DIM}     Messages: {len(messages)}, max tokens: {max_tokens or 'default'}{_RESET}")

    def sampling_response(self, text: str) -> None:
        print(f"{_DIM}     LLM responded: \"{_truncate(text)}\"{_RESET}")

    def sampling_error(self, cause: BaseException) -> None:
        print(f"{_RED}     Sampling error: {_get_error_message(cause)}{_RESET}", file=sys.stderr)

    def elicitation_request(self, mode: str) -> None:
        print(f"\n{_YELLOW}  🔔 Elicitation — server asked the client for user confirmation{_RESET}")
        print(f"{_DIM}     Mode: {mode}{_RESET}")

    def auto_accepted_elicitation(self, content: dict) -> None:
        print(f"{_DIM}     Auto-accepted with: {json.dumps(content)}{_RESET}")


client_log = _ClientLog()
