# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage statistics tracker — accumulates input/output/reasoning/cached
token counts across all API calls in a session.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/helpers/stats.js

"""

from typing import Any, Dict, Optional

_totals: Dict[str, int] = {
    "input": 0,
    "output": 0,
    "reasoning": 0,
    "cached": 0,
    "requests": 0,
}


def record_usage(usage: Optional[Dict[str, Any]]) -> None:
    """Accumulate token usage from an API response's usage object.

    Args:
        usage: The ``usage`` dict from a Responses API response, or None.
    """
    if not usage:
        return
    _totals["input"] += usage.get("input_tokens", 0)
    _totals["output"] += usage.get("output_tokens", 0)
    _totals["reasoning"] += (
        (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
    )
    _totals["cached"] += (
        (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    )
    _totals["requests"] += 1


def get_stats() -> Dict[str, int]:
    """Return a copy of the current accumulated totals."""
    return dict(_totals)


def log_stats() -> None:
    """Print a one-line token usage summary to stdout."""
    inp = _totals["input"]
    out = _totals["output"]
    reasoning = _totals["reasoning"]
    cached = _totals["cached"]
    requests = _totals["requests"]
    visible = out - reasoning

    summary = f"{requests} requests, {inp} in"
    if cached > 0:
        summary += f" ({cached} cached)"
    summary += f", {out} out"
    if reasoning > 0:
        summary += f" ({reasoning} reasoning + {visible} visible)"

    print(f"\n📊 Stats: {summary}\n")


def reset_stats() -> None:
    """Reset all counters to zero."""
    for key in _totals:
        _totals[key] = 0
