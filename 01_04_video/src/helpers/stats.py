# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage statistics tracker for OpenAI Responses API calls and Gemini video
processing calls. Module-level mutable state — reset per session with reset_stats().

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/stats.js`


"""

from typing import Any

# Mutable module-level state — intentional, mirrors JS module-scope variables.
_tokens: dict[str, int] = {"input": 0, "output": 0, "requests": 0}
_gemini_calls: dict[str, int] = {"generations": 0, "edits": 0, "analyses": 0}


def record_usage(usage: dict[str, Any] | None) -> None:
    """Accumulate token usage from an OpenAI Responses API response.

    Args:
        usage: The ``usage`` object from the API response, or ``None`` to skip.
    """
    if not usage:
        return
    _tokens["input"] += usage.get("input_tokens", 0)
    _tokens["output"] += usage.get("output_tokens", 0)
    _tokens["requests"] += 1


def record_gemini(type_: str) -> None:
    """Record a Gemini API call by type.

    Note: ``"upload"`` and ``"process"`` types (called from gemini.py) do not
    match any tracked counter — this mirrors the original JS behaviour where
    ``recordGemini("upload")`` and ``recordGemini("process")`` are effectively
    no-ops.

    Args:
        type_: One of ``"generate"``, ``"edit"``, ``"analyze"`` (others ignored).
    """
    if type_ == "generate":
        _gemini_calls["generations"] += 1
    elif type_ == "edit":
        _gemini_calls["edits"] += 1
    elif type_ == "analyze":
        _gemini_calls["analyses"] += 1


def get_stats() -> dict[str, dict[str, int]]:
    """Return a snapshot of current usage statistics.

    Returns:
        Dict with ``openai`` and ``gemini`` sub-dicts.
    """
    return {"openai": dict(_tokens), "gemini": dict(_gemini_calls)}


def log_stats() -> None:
    """Print usage statistics to stdout."""
    inp = _tokens["input"]
    out = _tokens["output"]
    req = _tokens["requests"]
    gen = _gemini_calls["generations"]
    ed = _gemini_calls["edits"]
    an = _gemini_calls["analyses"]
    print(f"\n📊 OpenAI Stats: {req} requests, {inp} input tokens, {out} output tokens")
    print(f"🎨 Gemini Stats: {gen} generations, {ed} edits, {an} analyses\n")


def reset_stats() -> None:
    """Zero all counters (called on REPL ``clear`` command)."""
    _tokens.update({"input": 0, "output": 0, "requests": 0})
    _gemini_calls.update({"generations": 0, "edits": 0, "analyses": 0})
