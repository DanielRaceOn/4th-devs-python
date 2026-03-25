# -*- coding: utf-8 -*-

#   tokens.py

"""
### Description:
Token estimation utilities for the 02_05_agent module.

Provides raw (chars/4) and calibrated token estimates for individual
messages and message lists.  Calibration adjusts the ratio based on
actual API-reported usage once 500+ tokens have been observed, making
budget calculations more accurate over a long conversation.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/ai/tokens.ts


"""

import math
from typing import Optional

from ..config import TOKEN_CHARS_PER_TOKEN, TOKEN_SAFETY_MARGIN


# ---------------------------------------------------------------------------
# Type aliases (mirror types.ts structures as plain dicts for simplicity)
# ---------------------------------------------------------------------------

# CalibrationState: {"cumulative_estimated": int, "cumulative_actual": int}
# Message: TextMessage | FunctionCallItem | FunctionCallOutputItem
# UsageTotals: {"estimated": int, "actual": int}


def estimate_tokens_raw(text: str) -> int:
    """Stable chars/4 estimate with no calibration applied.

    Used for threshold comparisons where predictability matters more than
    accuracy.

    Args:
        text: Input text.

    Returns:
        Estimated token count (ceiling of len/4).
    """
    if not text:
        return 0
    return math.ceil(len(text) / TOKEN_CHARS_PER_TOKEN)


def estimate_tokens(text: str, cal: Optional[dict] = None) -> int:
    """Calibrated token estimate.

    Adjusts the raw chars/4 estimate by the observed actual/estimated ratio
    once at least 500 actual tokens have been recorded.  Used for display
    and budget calculations.

    Args:
        text: Input text.
        cal: Optional calibration state dict with keys
            ``cumulative_estimated`` and ``cumulative_actual``.

    Returns:
        Estimated token count.
    """
    base = estimate_tokens_raw(text)
    if not base:
        return 0

    if cal and cal["cumulative_actual"] > 500 and cal["cumulative_estimated"] > 0:
        ratio = cal["cumulative_actual"] / cal["cumulative_estimated"]
        return math.ceil(base * ratio)

    return base


def with_safety_margin(tokens: int) -> int:
    """Apply the configured safety margin to a token count.

    Args:
        tokens: Raw estimated token count.

    Returns:
        Count multiplied by ``TOKEN_SAFETY_MARGIN``, ceiling-rounded.
    """
    return math.ceil(tokens * TOKEN_SAFETY_MARGIN)


def estimate_message_tokens(message: dict, cal: Optional[dict] = None) -> int:
    """Estimate tokens for a single message item.

    Handles all three message types (text, function_call,
    function_call_output).  Adds a 4-token overhead per message and an
    extra 10 tokens for function call metadata.

    Args:
        message: Message dict (TextMessage, FunctionCallItem, or
            FunctionCallOutputItem).
        cal: Optional calibration state.

    Returns:
        Estimated token count for this message.
    """
    tokens = 4  # per-message overhead

    msg_type = message.get("type")

    if msg_type == "function_call":
        tokens += estimate_tokens(message.get("name", ""), cal)
        tokens += estimate_tokens(message.get("arguments", ""), cal)
        tokens += 10  # function-call structural overhead
        return tokens

    if msg_type == "function_call_output":
        tokens += estimate_tokens(message.get("output", ""), cal)
        return tokens

    # TextMessage: has "role" and "content", no "type" field
    content = message.get("content")
    if isinstance(content, str):
        tokens += estimate_tokens(content, cal)
    return tokens


def estimate_messages_tokens(
    messages: list[dict], cal: Optional[dict] = None
) -> dict[str, int]:
    """Estimate tokens for a list of messages.

    Args:
        messages: List of message dicts.
        cal: Optional calibration state.

    Returns:
        Dict with keys ``raw`` (sum) and ``safe`` (with safety margin).
    """
    raw = sum(estimate_message_tokens(m, cal) for m in messages)
    return {"raw": raw, "safe": with_safety_margin(raw)}


def estimate_messages_tokens_raw(messages: list[dict]) -> int:
    """Raw (uncalibrated) total token estimate for a message list.

    Used for stable threshold comparisons.

    Args:
        messages: List of message dicts.

    Returns:
        Sum of raw per-message estimates.
    """
    return sum(estimate_message_tokens(m) for m in messages)


def record_actual_usage(cal: dict, estimated: int, actual: int) -> None:
    """Update calibration state with a new actual/estimated pair.

    Args:
        cal: Calibration state dict (mutated in place).
        estimated: The estimated token count that was predicted.
        actual: The actual token count reported by the API.
    """
    cal["cumulative_estimated"] += estimated
    cal["cumulative_actual"] += actual


def track_usage(
    usage: Optional[dict],
    cal: dict,
    estimated_safe: int,
    totals: dict,
) -> Optional[int]:
    """Record usage and update running totals.

    Args:
        usage: API usage dict with ``input_tokens`` and ``output_tokens``,
            or ``None`` if unavailable.
        cal: Calibration state dict (mutated in place).
        estimated_safe: The safety-margined estimate for this request.
        totals: Running totals dict with ``estimated`` and ``actual`` keys
            (mutated in place).

    Returns:
        Total actual tokens for this request, or ``None`` if usage was
        unavailable.
    """
    totals["estimated"] += estimated_safe
    if not usage:
        return None

    actual = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    totals["actual"] += actual
    record_actual_usage(cal, estimated_safe, actual)
    return actual


def get_calibration(cal: dict) -> dict:
    """Return the current calibration ratio and sample count.

    Args:
        cal: Calibration state dict.

    Returns:
        Dict with ``ratio`` (float or None) and ``samples`` (int).
    """
    if cal["cumulative_actual"] < 100 or cal["cumulative_estimated"] == 0:
        return {"ratio": None, "samples": cal["cumulative_actual"]}
    return {
        "ratio": cal["cumulative_actual"] / cal["cumulative_estimated"],
        "samples": cal["cumulative_actual"],
    }
