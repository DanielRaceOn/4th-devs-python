# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and cache hit rate tracking.
Records cumulative stats from each Responses API call and logs
a summary at the end of the run.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/helpers/stats.js`

"""

from __future__ import annotations
from typing import Optional

# Module-level mutable stats (reset per Python process)
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


def get_stats() -> dict:
    """Return current stats with a calculated cache hit rate.

    Returns:
        Dict with all counters plus ``cacheHitRate`` percentage string.
    """
    input_tokens = _stats["inputTokens"]
    cache_rate = (
        f"{(_stats['cachedTokens'] / input_tokens * 100):.1f}%"
        if input_tokens > 0
        else "0%"
    )
    return {**_stats, "cacheHitRate": cache_rate}


def log_stats() -> None:
    """Print a one-line stats summary to stdout."""
    from .logger import log
    s = get_stats()
    log.info(
        f"📊 Stats: {s['requests']} requests | {s['totalTokens']} tokens | "
        f"Cache: {s['cacheHitRate']} ({s['cachedTokens']}/{s['inputTokens']})"
    )
