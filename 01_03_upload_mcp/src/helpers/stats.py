# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and cache hit rate tracking.
Records cumulative stats from each Responses API call
and prints a summary at the end of the run.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/helpers/stats.js`

"""

from __future__ import annotations
from typing import Optional

_stats: dict = {
    "requests": 0,
    "inputTokens": 0,
    "cachedTokens": 0,
    "outputTokens": 0,
    "totalTokens": 0,
}


def record_usage(usage: Optional[dict]) -> None:
    """Accumulate token usage from an API response.

    Args:
        usage: The ``usage`` field from a Responses API response dict.
    """
    if not usage:
        return

    _stats["requests"] += 1
    _stats["inputTokens"] += usage.get("input_tokens", 0)
    _stats["cachedTokens"] += (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    _stats["outputTokens"] += usage.get("output_tokens", 0)
    _stats["totalTokens"] += usage.get("total_tokens", 0)


def log_stats() -> None:
    """Print a one-line stats summary to stdout."""
    from .logger import log
    inp = _stats["inputTokens"]
    cache_rate = (
        f"{_stats['cachedTokens'] / inp * 100:.1f}%"
        if inp > 0
        else "0%"
    )
    log.info(
        f"📊 Stats: {_stats['requests']} requests | {_stats['totalTokens']} tokens | "
        f"Cache: {cache_rate} ({_stats['cachedTokens']}/{inp})"
    )
