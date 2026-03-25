# -*- coding: utf-8 -*-

#   context.py

"""
### Description:
Context assembly helpers for the memory subsystem.

Provides the tail-budget split algorithm (keeps the most-recent messages that
fit within a token budget) and two context-building functions:

- ``build_passthrough_context`` — used when the observation threshold is not
  yet reached; observations are injected into the system prompt only.
- ``build_observed_context``   — used after the observer has run; the sealed
  head is replaced by observations and only the unobserved tail is sent.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/context.ts


"""

from typing import Optional

from ..types import is_function_call_output
from ..ai.tokens import estimate_message_tokens
from .prompts import CONTINUATION_HINT, build_observation_appendix


def split_by_tail_budget(
    messages: list[dict],
    tail_budget: int,
    calibration: Optional[dict] = None,
) -> dict:
    """Split *messages* into a head and a recent tail that fits the budget.

    Iterates from the end, accumulating token estimates until the budget is
    exceeded.  Then adjusts the split point backwards to avoid starting in the
    middle of a function-call/output pair.

    Args:
        messages: Full list of message dicts to split.
        tail_budget: Maximum token budget for the tail.
        calibration: Optional calibration state for adjusted estimates.

    Returns:
        Dict with keys ``head`` (list) and ``tail`` (list).
    """
    tail_tokens = 0
    split_index = len(messages)

    for i in range(len(messages) - 1, -1, -1):
        tokens = estimate_message_tokens(messages[i], calibration)
        if tail_tokens + tokens > tail_budget:
            break
        tail_tokens += tokens
        split_index = i

    # Don't start the tail in the middle of a function_call_output — step back
    while 0 < split_index < len(messages):
        if is_function_call_output(messages[split_index]):
            split_index -= 1
        else:
            break

    return {
        "head": messages[:split_index],
        "tail": messages[split_index:],
    }


def build_passthrough_context(session: dict, base_system_prompt: str) -> dict:
    """Build context without running the observer.

    If observations exist they are appended to the system prompt.  When the
    session has observations the message list is trimmed to the unobserved
    tail so the agent doesn't see messages that are already summarised.

    Args:
        session: Session dict containing ``messages`` and ``memory``.
        base_system_prompt: Agent base system prompt.

    Returns:
        ProcessedContext dict with keys ``system_prompt`` and ``messages``.
    """
    messages = session["messages"]
    memory = session["memory"]
    has_observations = bool(memory.get("active_observations"))
    unobserved = messages[memory.get("last_observed_index", 0):]

    return {
        "system_prompt": (
            f"{base_system_prompt}\n\n{build_observation_appendix(memory['active_observations'])}"
            if has_observations
            else base_system_prompt
        ),
        "messages": unobserved if has_observations else messages,
    }


def build_observed_context(session: dict, base_system_prompt: str) -> dict:
    """Build context after the observer has sealed the message head.

    The observations are injected into the system prompt.  If the unobserved
    tail is empty a continuation hint is used so the model doesn't see an
    empty input.

    Args:
        session: Session dict containing ``messages`` and ``memory``.
        base_system_prompt: Agent base system prompt.

    Returns:
        ProcessedContext dict with keys ``system_prompt`` and ``messages``.
    """
    messages = session["messages"]
    memory = session["memory"]
    remaining = messages[memory.get("last_observed_index", 0):]

    context_messages = remaining if remaining else [{"role": "user", "content": CONTINUATION_HINT}]

    return {
        "system_prompt": f"{base_system_prompt}\n\n{build_observation_appendix(memory['active_observations'])}",
        "messages": context_messages,
    }
