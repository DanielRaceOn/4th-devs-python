# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage statistics tracker. Accumulates input/output/reasoning/cached token
counts and request counts across all API calls in a session.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/stats.js`

"""

from typing import Any

_total: dict[str, int] = {
    "input": 0,
    "output": 0,
    "reasoning": 0,
    "cached": 0,
    "requests": 0,
}


def record_usage(usage: dict[str, Any] | None) -> None:
    """Accumulate token counts from an API response usage object.

    Args:
        usage: The ``usage`` field from an API response, or ``None`` to skip.
    """
    if not usage:
        return
    _total["input"] += usage.get("input_tokens", 0)
    _total["output"] += usage.get("output_tokens", 0)
    _total["reasoning"] += (
        (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
    )
    _total["cached"] += (
        (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    )
    _total["requests"] += 1


def get_stats() -> dict[str, int]:
    """Return a copy of the current accumulated token stats."""
    return dict(_total)


def log_stats() -> None:
    """Print a summary of accumulated token usage to stdout."""
    inp = _total["input"]
    out = _total["output"]
    reas = _total["reasoning"]
    cached = _total["cached"]
    reqs = _total["requests"]
    visible = out - reas

    summary = f"{reqs} requests, {inp} in"
    if cached > 0:
        summary += f" ({cached} cached)"
    summary += f", {out} out"
    if reas > 0:
        summary += f" ({reas} reasoning + {visible} visible)"

    print(f"\n📊 Stats: {summary}\n")


def reset_stats() -> None:
    """Reset all accumulated token counts to zero."""
    for key in _total:
        _total[key] = 0
