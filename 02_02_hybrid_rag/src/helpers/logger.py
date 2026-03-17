# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Colored terminal logger with ANSI escape codes. Provides generic log levels
(info, success, error, warn, start, box) plus specialized methods for the
hybrid RAG agent (query, response, api, tool, search phases).

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/helpers/logger.js

"""

from datetime import datetime
from typing import Any, Dict, List, Optional

# ── ANSI escape codes ─────────────────────────────────────────────────────────

_R = "\x1b[0m"   # reset
_B = "\x1b[1m"   # bright/bold
_D = "\x1b[2m"   # dim
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


# ── Generic levels ────────────────────────────────────────────────────────────

def info(msg: str) -> None:
    """Log an informational message."""
    print(f"{_D}[{_ts()}]{_R} {msg}")


def success(msg: str) -> None:
    """Log a success message with a green checkmark."""
    print(f"{_D}[{_ts()}]{_R} {_GRN}\u2713{_R} {msg}")


def error(title: str, msg: str = "") -> None:
    """Log an error with a red X."""
    print(f"{_D}[{_ts()}]{_R} {_RED}\u2717 {title}{_R} {msg}")


def warn(msg: str) -> None:
    """Log a warning with a yellow triangle."""
    print(f"{_D}[{_ts()}]{_R} {_YEL}\u26a0{_R} {msg}")


def start(msg: str) -> None:
    """Log a start/progress message with a cyan arrow."""
    print(f"{_D}[{_ts()}]{_R} {_CYN}\u2192{_R} {msg}")


def box(text: str) -> None:
    """Print a framed box around multi-line *text*."""
    lines = text.split("\n")
    width = max(len(l) for l in lines) + 4
    border = "\u2500" * width
    print(f"\n{_CYN}{border}{_R}")
    for line in lines:
        print(f"{_CYN}\u2502{_R} {_B}{line.ljust(width - 3)}{_R}{_CYN}\u2502{_R}")
    print(f"{_CYN}{border}{_R}\n")


# ── Agent-specific ────────────────────────────────────────────────────────────

def query(q: str) -> None:
    """Print the user's query in a highlighted banner."""
    print(f"\n{_BG_BLU}{_WHT} QUERY {_R} {q}\n")


def response(r: str) -> None:
    """Print the assistant's response (truncated at 500 chars)."""
    truncated = r[:500] + ("..." if len(r) > 500 else "")
    print(f"\n{_GRN}Response:{_R} {truncated}\n")


def api(step: str, msg_count: int) -> None:
    """Log an API call step with message count."""
    print(f"{_D}[{_ts()}]{_R} {_MAG}\u25c6{_R} {step} ({msg_count} messages)")


def api_done(usage: Optional[Dict[str, Any]]) -> None:
    """Log token usage after an API call completes."""
    if not usage:
        return
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
    visible = out - reasoning

    parts = [f"{inp} in"]
    if cached > 0:
        parts.append(f"{cached} cached")
    parts.append(f"{out} out")
    if reasoning > 0:
        parts.append(f"{_CYN}{reasoning} reasoning{_D} + {visible} visible")

    print(f"{_D}         tokens: {' / '.join(parts)}{_R}")


def reasoning(summaries: List[str]) -> None:
    """Print reasoning summaries (one block per summary)."""
    if not summaries:
        return
    print(f"{_D}         {_CYN}reasoning:{_R}")
    for summary in summaries:
        for line in summary.split("\n"):
            print(f"{_D}           {line}{_R}")


def tool(name: str, args: Any) -> None:
    """Log a tool call with its arguments."""
    import json
    arg_str = json.dumps(args)
    truncated = arg_str[:300] + ("..." if len(arg_str) > 300 else "")
    print(f"{_D}[{_ts()}]{_R} {_YEL}\u26a1{_R} {name} {_D}{truncated}{_R}")


def tool_result(name: str, ok: bool, output: str) -> None:
    """Log the result of a tool call."""
    icon = f"{_GRN}\u2713{_R}" if ok else f"{_RED}\u2717{_R}"
    truncated = output[:500] + ("..." if len(output) > 500 else "")
    print(f"{_D}         {icon} {truncated}{_R}")


# ── Search-specific ───────────────────────────────────────────────────────────

def search_header(keywords: str, semantic: str) -> None:
    """Print the FTS and semantic query strings before a hybrid search."""
    print(f'{_D}         {_CYN}fts:{_R}{_D}      "{keywords}"{_R}')
    print(f'{_D}         {_CYN}semantic:{_R}{_D} "{semantic}"{_R}')


def search_fts(results: List[Dict[str, Any]]) -> None:
    """Log FTS5 search results."""
    label = f"{_BLU}FTS{_R}"
    if not results:
        print(f"{_D}         {label} {_D}(no matches){_R}")
        return
    print(f"{_D}         {label} {len(results)} hit(s){_R}")
    for r in results[:5]:
        section = f" \u2192 {r['section']}" if r.get("section") else ""
        score = f"{r['fts_score']:.2f}" if r.get("fts_score") is not None else "?"
        terms = r.get("matched_terms", [])
        term_str = (
            f" {_YEL}[{', '.join(terms)}]{_R}{_D}" if terms else ""
        )
        print(f"{_D}           #{r['chunk_index']} {r['source']}{section} (bm25: {score}){term_str}{_R}")
    if len(results) > 5:
        print(f"{_D}           ... +{len(results) - 5} more{_R}")


def search_vec(results: List[Dict[str, Any]]) -> None:
    """Log vector search results."""
    label = f"{_MAG}VEC{_R}"
    if not results:
        print(f"{_D}         {label} {_D}(no matches){_R}")
        return
    print(f"{_D}         {label} {len(results)} hit(s){_R}")
    for r in results[:5]:
        section = f" \u2192 {r['section']}" if r.get("section") else ""
        dist = f"{r['vec_distance']:.3f}" if r.get("vec_distance") is not None else "?"
        print(f"{_D}           #{r['chunk_index']} {r['source']}{section} (dist: {dist}){_R}")
    if len(results) > 5:
        print(f"{_D}           ... +{len(results) - 5} more{_R}")


def search_rrf(results: List[Dict[str, Any]]) -> None:
    """Log the final RRF-merged search results."""
    label = f"{_GRN}RRF{_R}"
    print(f"{_D}         {label} {len(results)} merged result(s){_R}")
    for r in results:
        section = f" \u2192 {r['section']}" if r.get("section") else ""
        fts = f"fts:#{r['fts_rank']}" if r.get("fts_rank") else "\u2014"
        vec = f"vec:#{r['vec_rank']}" if r.get("vec_rank") else "\u2014"
        rrf = f"{r['rrf']:.4f}" if r.get("rrf") is not None else "?"
        print(f"{_D}           {r['source']}{section} [{fts} {vec}] rrf={rrf}{_R}")
