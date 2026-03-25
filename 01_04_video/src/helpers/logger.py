# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Simple colored terminal logger using ANSI escape codes. No external dependencies.
Mirrors the JavaScript logger.js default export as a module-level ``log`` singleton.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/logger.js`


"""

import json
from datetime import datetime

# ANSI escape codes — same palette as the JS version
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


def _ts() -> str:
    """Return current time in HH:MM:SS format (matches JS toLocaleTimeString)."""
    return datetime.now().strftime("%H:%M:%S")


class _Logger:
    """Colored terminal logger matching the JavaScript logger.js API surface."""

    def info(self, msg: str) -> None:
        """Dim timestamp + plain message."""
        print(f"{_DIM}[{_ts()}]{_RESET} {msg}")

    def success(self, msg: str) -> None:
        """Dim timestamp + green checkmark."""
        print(f"{_DIM}[{_ts()}]{_RESET} {_GREEN}✓{_RESET} {msg}")

    def error(self, title: str, msg: str = "") -> None:
        """Dim timestamp + red X."""
        print(f"{_DIM}[{_ts()}]{_RESET} {_RED}✗ {title}{_RESET} {msg}")

    def warn(self, msg: str) -> None:
        """Dim timestamp + yellow warning."""
        print(f"{_DIM}[{_ts()}]{_RESET} {_YELLOW}⚠{_RESET} {msg}")

    def start(self, msg: str) -> None:
        """Dim timestamp + cyan arrow."""
        print(f"{_DIM}[{_ts()}]{_RESET} {_CYAN}→{_RESET} {msg}")

    def box(self, text: str) -> None:
        """Cyan bordered box; supports multi-line text."""
        lines = text.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{_CYAN}{'─' * width}{_RESET}")
        for line in lines:
            print(
                f"{_CYAN}│{_RESET} {_BRIGHT}{line.ljust(width - 3)}{_RESET}"
                f"{_CYAN}│{_RESET}"
            )
        print(f"{_CYAN}{'─' * width}{_RESET}\n")

    def query(self, q: str) -> None:
        """Blue-background QUERY badge + text."""
        print(f"\n{_BG_BLUE}{_WHITE} QUERY {_RESET} {q}\n")

    def response(self, r: str) -> None:
        """Green 'Response:' prefix, truncated to 500 chars."""
        truncated = r[:500] + ("..." if len(r) > 500 else "")
        print(f"\n{_GREEN}Response:{_RESET} {truncated}\n")

    def api(self, step: str, msg_count: int) -> None:
        """Magenta diamond, step label and message count."""
        print(
            f"{_DIM}[{_ts()}]{_RESET} {_MAGENTA}◆{_RESET} {step} ({msg_count} messages)"
        )

    def api_done(self, usage: dict | None) -> None:
        """Dim token usage line."""
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            print(f"{_DIM}         tokens: {inp} in / {out} out{_RESET}")

    def tool(self, name: str, args: dict) -> None:
        """Yellow lightning bolt + tool name + truncated args."""
        arg_str = json.dumps(args)
        truncated = arg_str[:100] + ("..." if len(arg_str) > 100 else "")
        print(
            f"{_DIM}[{_ts()}]{_RESET} {_YELLOW}⚡{_RESET} {name} {_DIM}{truncated}{_RESET}"
        )

    def tool_result(self, name: str, success: bool, output: str) -> None:
        """Green checkmark or red X + truncated output."""
        icon = f"{_GREEN}✓{_RESET}" if success else f"{_RED}✗{_RESET}"
        truncated = output[:150] + ("..." if len(output) > 150 else "")
        print(f"{_DIM}         {icon} {truncated}{_RESET}")

    def gemini(self, action: str, detail: str = "") -> None:
        """Magenta-background GEMINI badge + action."""
        print(
            f"{_DIM}[{_ts()}]{_RESET} {_BG_MAGENTA}{_WHITE} GEMINI {_RESET} {action}"
        )
        if detail:
            print(f"{_DIM}         {detail}{_RESET}")

    def gemini_result(self, success: bool, msg: str) -> None:
        """Green or red icon + Gemini result message."""
        icon = f"{_GREEN}✓{_RESET}" if success else f"{_RED}✗{_RESET}"
        print(f"{_DIM}         {icon} {msg}{_RESET}")


# Module-level singleton — import as ``from .logger import log``
log = _Logger()
