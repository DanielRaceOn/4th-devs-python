# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Logger — colored terminal output with smart summarization.
Provides [LABEL] tags and truncated tool args/results instead of
raw JSON dumps, keeping the output readable during long agent runs.

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
_MAGENTA = "\x1b[35m"
_CYAN = "\x1b[36m"


def _tag(name: str, color: str) -> str:
    return f"{_BOLD}{color}[{name}]{_RESET}"


def _truncate(text: str, max_len: int = 120) -> str:
    return text[:max_len - 1] + "…" if len(text) > max_len else text


def _summarize_args(name: str, args: dict) -> str:
    if "fs_read" in name and "path" in args:
        return f"{args['path']} ({args.get('mode', 'content')})"
    if "fs_write" in name and "path" in args:
        return f"{args['path']} ({args.get('operation', '?')})"
    if "fs_search" in name and "query" in args:
        return f"\"{args['query']}\" in {args.get('path', '.')}"
    if "fs_manage" in name and "operation" in args:
        return f"{args['operation']} {args.get('path', '')}"
    if "upload_files" in name and "files" in args:
        return ", ".join(f.get("name", "?") for f in args["files"])
    if "list_files" in name:
        return ""
    return _truncate(json.dumps(args), 80)


def _summarize_result(name: str, result: Any) -> str:
    if isinstance(result, str):
        return _truncate(result, 100)
    if isinstance(result, dict):
        if result.get("success") and result.get("type") == "file":
            lines = (result.get("content") or {}).get("totalLines", "?")
            return f"✓ {result.get('path')} ({lines} lines)"
        if result.get("success") and result.get("type") == "directory":
            return f"✓ {result.get('summary', '')}"
        if result.get("status") == "applied":
            action = (result.get("result") or {}).get("action", "written")
            return f"✓ {action}"
        if result.get("status") == "error":
            msg = (result.get("error") or {}).get("message", "failed")
            return f"✗ {msg}"
        if "status" in result:
            return str(result["status"])
    return f"{len(json.dumps(result))} chars"


def _try_parse_json(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


class _Logger:
    def info(self, msg: str) -> None:
        print(f"{_DIM}  {msg}{_RESET}")

    def success(self, msg: str) -> None:
        print(f"  {_GREEN}✓{_RESET} {msg}")

    def warn(self, msg: str) -> None:
        print(f"  {_YELLOW}⚠{_RESET} {msg}")

    def error(self, msg: str, detail: Optional[str] = None) -> None:
        suffix = f": {detail}" if detail else ""
        print(f"  {_RED}✗ {msg}{suffix}{_RESET}", file=sys.stderr)

    def debug(self, msg: str) -> None:
        pass  # Suppress debug by default

    def box(self, msg: str) -> None:
        lines = msg.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{_BOLD}╭{'─' * width}╮{_RESET}")
        for line in lines:
            print(f"{_BOLD}│  {line.ljust(width - 2)}│{_RESET}")
        print(f"{_BOLD}╰{'─' * width}╯{_RESET}\n")

    def start(self, msg: str) -> None:
        print(f"  {_CYAN}◐{_RESET} {msg}")

    def ready(self, msg: str) -> None:
        print(f"  {_GREEN}✓{_RESET} {_BOLD}{msg}{_RESET}")

    def tool(self, name: str, args: dict) -> None:
        summary = _summarize_args(name, args)
        print(f"  {_tag('TOOL', _MAGENTA)} {_CYAN}{name}{_RESET} {_DIM}{summary}{_RESET}")

    def tool_result(self, name: str, success: bool, detail: str = "") -> None:
        if success:
            parsed = _try_parse_json(detail)
            summary = _summarize_result(name, parsed) if parsed is not None else _truncate(detail, 100)
            print(f"  {_DIM}  → {summary}{_RESET}")
        else:
            print(f"  {_RED}  → ✗ {_truncate(detail, 100)}{_RESET}")

    def api(self, action: str, history_length: Optional[int] = None) -> None:
        info = f" ({history_length} msgs)" if history_length is not None else ""
        print(f"\n  {_tag('LLM', _BLUE)} {action}{_DIM}{info}{_RESET}")

    def api_done(self, usage: Optional[dict]) -> None:
        if not usage:
            return
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        rate = round(cached / inp * 100) if inp > 0 else 0
        print(f"  {_DIM}  → {inp} in, {out} out, {rate}% cached{_RESET}")

    def query(self, text: str) -> None:
        print(f"\n{_tag('QUERY', _BLUE)} {_truncate(text, 120)}")

    def response(self, text: str) -> None:
        print(f"\n{_tag('DONE', _GREEN)} {_truncate(text, 120)}\n")


log = _Logger()
