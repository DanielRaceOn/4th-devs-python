# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and API call statistics tracker.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      helpers/stats.js

"""

# Global state for token tracking
_total_tokens = {"input": 0, "output": 0, "requests": 0}
_gemini_calls = {"generations": 0, "edits": 0, "analyses": 0}


def record_usage(usage: dict) -> None:
    """Record token usage from API response."""
    if not usage:
        return
    global _total_tokens
    _total_tokens["input"] += usage.get("input_tokens", 0)
    _total_tokens["output"] += usage.get("output_tokens", 0)
    _total_tokens["requests"] += 1


def record_gemini(call_type: str) -> None:
    """Record Gemini API call type."""
    global _gemini_calls
    if call_type == "generate":
        _gemini_calls["generations"] += 1
    elif call_type == "edit":
        _gemini_calls["edits"] += 1
    elif call_type in ("analyze", "analyze_video"):
        _gemini_calls["analyses"] += 1


def get_stats() -> dict:
    """Get current statistics."""
    return {
        "openai": _total_tokens.copy(),
        "gemini": _gemini_calls.copy(),
    }


def log_stats() -> None:
    """Print statistics to console."""
    input_tokens = _total_tokens["input"]
    output_tokens = _total_tokens["output"]
    requests = _total_tokens["requests"]
    generations = _gemini_calls["generations"]
    edits = _gemini_calls["edits"]
    analyses = _gemini_calls["analyses"]

    print(
        f"\n📊 OpenAI Stats: {requests} requests, {input_tokens} input tokens, {output_tokens} output tokens"
    )
    print(f"🎨 Gemini Stats: {generations} generations, {edits} edits, {analyses} analyses\n")


def reset_stats() -> None:
    """Reset all statistics."""
    global _total_tokens, _gemini_calls
    _total_tokens = {"input": 0, "output": 0, "requests": 0}
    _gemini_calls = {"generations": 0, "edits": 0, "analyses": 0}
