# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Simple colored terminal logger — mirrors the JS helpers/logger.js.
Provides timestamped, color-coded log methods for info, success, error,
search progress, tool calls, API steps, and reasoning display.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/logger.js`

"""

import json
import sys
from datetime import datetime


# ── ANSI color codes ──────────────────────────────────────────────────────────

_R = "\x1b[0m"   # reset
_B = "\x1b[1m"   # bright
_DM = "\x1b[2m"  # dim
_RED = "\x1b[31m"
_GRN = "\x1b[32m"
_YEL = "\x1b[33m"
_BLU = "\x1b[34m"
_MAG = "\x1b[35m"
_CYN = "\x1b[36m"
_WHT = "\x1b[37m"
_BG_BLU = "\x1b[44m"
_BG_MAG = "\x1b[45m"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


class _Logger:
    """Colored terminal logger with timestamped output."""

    def _print(self, msg: str) -> None:
        print(msg, flush=True)

    def info(self, msg: str) -> None:
        self._print(f"{_DM}[{_ts()}]{_R} {msg}")

    def success(self, msg: str) -> None:
        self._print(f"{_DM}[{_ts()}]{_R} {_GRN}✓{_R} {msg}")

    def error(self, title: str, msg: str = "") -> None:
        self._print(f"{_DM}[{_ts()}]{_R} {_RED}✗ {title}{_R} {msg}")

    def warn(self, msg: str) -> None:
        self._print(f"{_DM}[{_ts()}]{_R} {_YEL}⚠{_R} {msg}")

    def start(self, msg: str) -> None:
        self._print(f"{_DM}[{_ts()}]{_R} {_CYN}→{_R} {msg}")

    def box(self, text: str) -> None:
        lines = text.split("\n")
        width = max(len(l) for l in lines) + 4
        bar = "─" * width
        print(f"\n{_CYN}{bar}{_R}")
        for line in lines:
            print(f"{_CYN}│{_R} {_B}{line.ljust(width - 3)}{_R}{_CYN}│{_R}")
        print(f"{_CYN}{bar}{_R}\n")

    def query(self, q: str) -> None:
        self._print(f"\n{_BG_BLU}{_WHT} QUERY {_R} {q}\n")

    def response(self, r: str) -> None:
        truncated = r[:500] + ("..." if len(r) > 500 else "")
        self._print(f"\n{_GRN}Response:{_R} {truncated}\n")

    def api(self, step: str, msg_count: int) -> None:
        self._print(
            f"{_DM}[{_ts()}]{_R} {_MAG}◆{_R} {step} ({msg_count} messages)"
        )

    def api_done(self, usage: dict | None) -> None:
        if not usage:
            return
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        visible = usage.get("output_tokens", 0) - reasoning

        parts = [f"{usage.get('input_tokens', 0)} in"]
        if cached > 0:
            parts.append(f"{cached} cached")
        parts.append(f"{usage.get('output_tokens', 0)} out")
        if reasoning > 0:
            parts.append(
                f"{_CYN}{reasoning} reasoning{_DM} + {visible} visible"
            )
        self._print(f"{_DM}         tokens: {' / '.join(parts)}{_R}")

    def reasoning(self, summaries: list[str]) -> None:
        if not summaries:
            return
        self._print(f"{_DM}         {_CYN}reasoning:{_R}")
        for summary in summaries:
            for line in summary.split("\n"):
                self._print(f"{_DM}           {line}{_R}")

    def tool(self, name: str, args: dict) -> None:
        arg_str = json.dumps(args)
        truncated = arg_str[:300] + ("..." if len(arg_str) > 300 else "")
        self._print(
            f"{_DM}[{_ts()}]{_R} {_YEL}⚡{_R} {name} {_DM}{truncated}{_R}"
        )

    def tool_result(self, name: str, success: bool, output: str) -> None:
        icon = f"{_GRN}✓{_R}" if success else f"{_RED}✗{_R}"
        truncated = output[:500] + ("..." if len(output) > 500 else "")
        self._print(f"{_DM}         {icon} {truncated}{_R}")

    # ── Search-specific logs ──────────────────────────────────────────────────

    def search_header(self, keywords: str, semantic: str) -> None:
        self._print(f'{_DM}         {_CYN}fts:{_R}{_DM}      "{keywords}"{_R}')
        self._print(f'{_DM}         {_CYN}semantic:{_R}{_DM} "{semantic}"{_R}')

    def search_fts(self, results: list) -> None:
        label = f"{_BLU}FTS{_R}"
        if not results:
            self._print(f"{_DM}         {label} {_DM}(no matches){_R}")
            return
        self._print(f"{_DM}         {label} {len(results)} hit(s){_R}")
        for r in results[:5]:
            src = r.get("source", "")
            section = f" → {r['section']}" if r.get("section") else ""
            score = f"{r['fts_score']:.2f}" if r.get("fts_score") is not None else "?"
            terms = r.get("matched_terms", [])
            term_str = (
                f" {_YEL}[{', '.join(terms)}]{_R}{_DM}" if terms else ""
            )
            self._print(
                f"{_DM}           #{r.get('chunk_index', '?')} "
                f"{src}{section} (bm25: {score}){term_str}{_R}"
            )
        if len(results) > 5:
            self._print(f"{_DM}           ... +{len(results) - 5} more{_R}")

    def search_vec(self, results: list) -> None:
        label = f"{_MAG}VEC{_R}"
        if not results:
            self._print(f"{_DM}         {label} {_DM}(no matches){_R}")
            return
        self._print(f"{_DM}         {label} {len(results)} hit(s){_R}")
        for r in results[:5]:
            src = r.get("source", "")
            section = f" → {r['section']}" if r.get("section") else ""
            dist = r.get("vec_distance")
            dist_str = f"{dist:.3f}" if dist is not None else "?"
            self._print(
                f"{_DM}           #{r.get('chunk_index', '?')} "
                f"{src}{section} (dist: {dist_str}){_R}"
            )
        if len(results) > 5:
            self._print(f"{_DM}           ... +{len(results) - 5} more{_R}")

    def search_rrf(self, results: list) -> None:
        label = f"{_GRN}RRF{_R}"
        self._print(f"{_DM}         {label} {len(results)} merged result(s){_R}")
        for r in results:
            src = r.get("source", "")
            section = f" → {r['section']}" if r.get("section") else ""
            fts = f"fts:#{r['fts_rank']}" if r.get("fts_rank") else "—"
            vec = f"vec:#{r['vec_rank']}" if r.get("vec_rank") else "—"
            rrf = f"{r['rrf']:.4f}" if r.get("rrf") is not None else "?"
            self._print(
                f"{_DM}           {src}{section} [{fts} {vec}] rrf={rrf}{_R}"
            )


log = _Logger()
