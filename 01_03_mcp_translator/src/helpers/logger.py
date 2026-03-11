# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Logging with rich-style colored output.
Replaces the JS ``consola`` library with a structured Python logger
that provides the same interface: info, success, warn, error, debug,
box, start, ready, tool, tool_result, api, api_done, query, response,
endpoint.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/helpers/logger.js`

"""

import json
import sys
from typing import Any, Optional

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_BLUE = "\x1b[34m"
_CYAN = "\x1b[36m"


def _truncate(text: str, max_len: int = 200) -> str:
    return text[:max_len - 3] + "..." if len(text) > max_len else text


class _Logger:
    def info(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  ℹ {msg}{' ' + extra if extra else ''}")

    def success(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_GREEN}✔{_RESET} {msg}{' ' + extra if extra else ''}")

    def warn(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_YELLOW}⚠{_RESET} {msg}{' ' + extra if extra else ''}")

    def error(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_RED}✗ {msg}{' ' + extra if extra else ''}{_RESET}", file=sys.stderr)

    def debug(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_DIM}◦ {msg}{' ' + extra if extra else ''}{_RESET}")

    def box(self, msg: str) -> None:
        lines = msg.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{_BOLD}╭{'─' * width}╮{_RESET}")
        for line in lines:
            print(f"{_BOLD}│  {line.ljust(width - 2)}│{_RESET}")
        print(f"{_BOLD}╰{'─' * width}╯{_RESET}\n")

    def start(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_CYAN}◐{_RESET} {msg}{' ' + extra if extra else ''}")

    def ready(self, msg: str, *args: Any) -> None:
        extra = " ".join(str(a) for a in args)
        print(f"  {_GREEN}✓{_RESET} {_BOLD}{msg}{' ' + extra if extra else ''}{_RESET}")

    def tool(self, name: str, args: Any) -> None:
        args_str = json.dumps(args) if isinstance(args, (dict, list)) else str(args)
        truncated = _truncate(args_str)
        self.info(f"🔧 {name} {truncated}")

    def tool_result(self, name: str, success: bool, detail: str = "") -> None:
        truncated = _truncate(detail)
        if success:
            print(f"  {_GREEN}✔{_RESET}   ↳ {truncated or 'OK'}")
        else:
            print(f"  {_RED}✗{_RESET}   ↳ {truncated or 'Failed'}", file=sys.stderr)

    def api(self, action: str, history_length: Optional[int] = None) -> None:
        info = f" ({history_length} messages)" if history_length is not None else ""
        self.info(f"🤖 {action}{info}")

    def api_done(self, usage: Optional[dict]) -> None:
        if not usage:
            print(f"  {_GREEN}✔{_RESET}   ↳ done")
            return
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        rate = round(cached / inp * 100) if inp > 0 else 0
        print(f"  {_GREEN}✔{_RESET}   ↳ in:{inp} out:{out} | cached:{cached} ({rate}%)")

    def query(self, text: str) -> None:
        truncated = _truncate(text, 60)
        self.info(f"▶ Query: {truncated}")

    def response(self, text: str) -> None:
        truncated = _truncate(text, 80)
        print(f"  {_GREEN}✔{_RESET} ◀ Response: {truncated}")

    def endpoint(self, method: str, path: str, desc: str) -> None:
        self.info(f"  {method.ljust(5)} {path.ljust(18)} {desc}")


log = _Logger()
