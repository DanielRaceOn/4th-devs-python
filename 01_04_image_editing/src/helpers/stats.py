# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and Gemini call statistics tracker.
Tracks both OpenAI Responses API tokens and Gemini image generation/editing calls.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/stats.js

"""

from typing import Optional

# Module-level mutable counters (reset between REPL sessions with reset_stats())
_total_tokens: dict = {"input": 0, "output": 0, "requests": 0}
_gemini_calls: dict = {"generations": 0, "edits": 0, "analyses": 0}


def record_usage(usage: Optional[dict]) -> None:
    """Accumulate OpenAI token counts from a Responses API usage dict.

    Args:
        usage: Usage dict with ``input_tokens`` and ``output_tokens`` fields.
               No-op if ``None`` or empty.
    """
    if not usage:
        return
    _total_tokens["input"] += usage.get("input_tokens", 0)
    _total_tokens["output"] += usage.get("output_tokens", 0)
    _total_tokens["requests"] += 1


def record_gemini(stats_type: str) -> None:
    """Increment the Gemini call counter for the given operation type.

    Args:
        stats_type: One of ``"generate"``, ``"edit"``, or ``"analyze"``.
    """
    if stats_type == "generate":
        _gemini_calls["generations"] += 1
    elif stats_type == "edit":
        _gemini_calls["edits"] += 1
    elif stats_type == "analyze":
        _gemini_calls["analyses"] += 1


def get_stats() -> dict:
    """Return a snapshot of current token and Gemini call stats.

    Returns:
        Dict with ``openai`` and ``gemini`` sub-dicts.
    """
    return {
        "openai": dict(_total_tokens),
        "gemini": dict(_gemini_calls),
    }


def log_stats() -> None:
    """Print accumulated token and Gemini call statistics to stdout."""
    inp = _total_tokens["input"]
    out = _total_tokens["output"]
    reqs = _total_tokens["requests"]
    gens = _gemini_calls["generations"]
    edits = _gemini_calls["edits"]
    analyses = _gemini_calls["analyses"]
    print(f"\n📊 OpenAI Stats: {reqs} requests, {inp} input tokens, {out} output tokens")
    print(f"🎨 Gemini Stats: {gens} generations, {edits} edits, {analyses} analyses\n")


def reset_stats() -> None:
    """Reset all counters to zero (called on REPL 'clear' command)."""
    global _total_tokens, _gemini_calls
    _total_tokens = {"input": 0, "output": 0, "requests": 0}
    _gemini_calls = {"generations": 0, "edits": 0, "analyses": 0}
