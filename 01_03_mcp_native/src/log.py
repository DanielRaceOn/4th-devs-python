# -*- coding: utf-8 -*-

#   log.py

"""
### Description:
Logging helpers for the MCP native demo.
Color-coded labels distinguish MCP tools from native tools in output.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/log.js`

"""

import json
from typing import Any

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_GREEN = "\x1b[32m"
_RED = "\x1b[31m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"

# Labels used by the unified handler map to identify the tool backend
MCP_LABEL = f"{_CYAN}🔌 MCP{_RESET}"
NATIVE_LABEL = f"{_YELLOW}⚡ Native{_RESET}"


def log_query(query: str) -> None:
    print(f"\n{_BOLD}{'═' * 60}{_RESET}")
    print(f"{_BOLD}Query: {query}{_RESET}")
    print(f"{_BOLD}{'═' * 60}{_RESET}")


def log_tool_call(label: str, name: str, args: Any) -> None:
    print(f"  {label} {_BOLD}{name}{_RESET}({_DIM}{json.dumps(args)}{_RESET})")


def log_tool_result(result: Any) -> None:
    print(f"       {_GREEN}✓{_RESET} {_DIM}{json.dumps(result)}{_RESET}")


def log_tool_error(message: str) -> None:
    print(f"       {_RED}✗ Error: {message}{_RESET}")


def log_tool_count(count: int) -> None:
    print(f"\n{_DIM}Tool calls: {count}{_RESET}")


def log_response(text: str) -> None:
    print(f"\n{_GREEN}Assistant:{_RESET} {text}")
