# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Colored terminal logger with styled output for the image editing agent.
Mirrors the JS logger with ANSI escape codes for color formatting.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/logger.js

"""

from datetime import datetime
from typing import Any, Optional


# ANSI color codes
_RESET = "\x1b[0m"
_BRIGHT = "\x1b[1m"
_DIM = "\x1b[2m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_BLUE = "\x1b[34m"
_MAGENTA = "\x1b[35m"
_CYAN = "\x1b[36m"
_WHITE = "\x1b[37m"
_BG_BLUE = "\x1b[44m"
_BG_MAGENTA = "\x1b[45m"


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _truncate(value: Any, max_len: int) -> str:
    text = str(value) if value is not None else ""
    return text[:max_len] + "..." if len(text) > max_len else text


class Logger:
    """Colored terminal logger for structured agent output."""

    def info(self, msg: str) -> None:
        """Log an informational message."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {msg}")

    def success(self, msg: str) -> None:
        """Log a success message with a green check mark."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_GREEN}✓{_RESET} {msg}")

    def error(self, title: str, msg: str = "") -> None:
        """Log an error with a red cross."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_RED}✗ {title}{_RESET} {msg}")

    def warn(self, msg: str) -> None:
        """Log a warning with a yellow warning symbol."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_YELLOW}⚠{_RESET} {msg}")

    def start(self, msg: str) -> None:
        """Log a start/progress message with a cyan arrow."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_CYAN}→{_RESET} {msg}")

    def box(self, text: str) -> None:
        """Print text inside a bordered box."""
        lines = text.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{_CYAN}{'─' * width}{_RESET}")
        for line in lines:
            print(f"{_CYAN}│{_RESET} {_BRIGHT}{line.ljust(width - 3)}{_RESET}{_CYAN}│{_RESET}")
        print(f"{_CYAN}{'─' * width}{_RESET}\n")

    def heading(self, title: str, description: Optional[str] = None) -> None:
        """Print a section heading."""
        print(f"\n{_BRIGHT}═══ {title} ═══{_RESET}")
        if description:
            print(f"{_DIM}{description}{_RESET}")

    def example(self, text: str) -> None:
        """Print an example query line."""
        print(f"  {_GREEN}→{_RESET} {_BRIGHT}{text}{_RESET}")

    def hint(self, text: str) -> None:
        """Print a dim hint line."""
        print(f"\n{_DIM}{text}{_RESET}\n")

    def query(self, q: str) -> None:
        """Print a user query block."""
        print(f"\n{_BG_BLUE}{_WHITE} QUERY {_RESET} {q}\n")

    def response(self, r: str) -> None:
        """Print a truncated response preview."""
        print(f"\n{_GREEN}Response:{_RESET} {_truncate(r, 500)}\n")

    def api(self, step: str, msg_count: int) -> None:
        """Log an API call step."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_MAGENTA}◆{_RESET} {step} ({msg_count} messages)")

    def api_done(self, usage: Optional[dict]) -> None:
        """Log token usage after an API call completes."""
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            print(f"{_DIM}         tokens: {inp} in / {out} out{_RESET}")

    def tool(self, name: str, args: Any) -> None:
        """Log a tool invocation."""
        import json
        arg_str = _truncate(json.dumps(args), 100)
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_YELLOW}⚡{_RESET} {name} {_DIM}{arg_str}{_RESET}")

    def tool_result(self, name: str, success: bool, output: str) -> None:
        """Log a tool result."""
        icon = f"{_GREEN}✓{_RESET}" if success else f"{_RED}✗{_RESET}"
        print(f"{_DIM}         {icon} {_truncate(output, 150)}{_RESET}")

    def vision(self, path: str, question: str) -> None:
        """Log a vision API call."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_BLUE}👁{_RESET} Vision: {path}")
        print(f"{_DIM}         Q: {question}{_RESET}")

    def vision_result(self, answer: str) -> None:
        """Log a vision API result."""
        print(f"{_DIM}         A: {_truncate(answer, 200)}{_RESET}")

    def gemini(self, action: str, detail: Optional[str] = None) -> None:
        """Log a Gemini image API call."""
        print(f"{_DIM}[{_timestamp()}]{_RESET} {_BG_MAGENTA}{_WHITE} GEMINI {_RESET} {action}")
        if detail:
            print(f"{_DIM}         {detail}{_RESET}")

    def gemini_result(self, success: bool, msg: str) -> None:
        """Log a Gemini image API result."""
        icon = f"{_GREEN}✓{_RESET}" if success else f"{_RED}✗{_RESET}"
        print(f"{_DIM}         {icon} {msg}{_RESET}")


log = Logger()
