# -*- coding: utf-8 -*-

#   runtime.py

"""
### Description:
Memory runtime — ``run_observation`` and ``run_reflection`` state-mutation helpers.

Each function takes the shared ``httpx.AsyncClient``, the current session, and
the memory config, then mutates ``session["memory"]`` in place and writes a
persistence log entry.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/runtime.ts


"""

import httpx

from ..config import resolve_model_for_provider
from ..ai.tokens import estimate_tokens
from ..helpers.log import log
from .observer import run_observer
from .reflector import run_reflector
from .context import split_by_tail_budget
from .persistence import persist_observer_log, persist_reflector_log

# Minimum tail budget prevents the observer from consuming 100 % of unobserved messages.
_MIN_TAIL_BUDGET = 120
# Fraction of observationThresholdTokens reserved as "recent tail" left unobserved.
_OBSERVATION_TAIL_RATIO = 0.3


async def run_observation(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    session: dict,
    config: dict,
) -> None:
    """Seal the head of the unobserved message list into observation memory.

    Splits unobserved messages so a recent tail is kept raw (below the
    ``_MIN_TAIL_BUDGET`` / ``_OBSERVATION_TAIL_RATIO`` threshold), then sends
    the head to the observer.  Updates ``session["memory"]`` in place.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        session: Session dict (mutated in place via ``session["memory"]``).
        config: MemoryConfig dict.
    """
    messages = session["messages"]
    memory = session["memory"]
    unobserved = messages[memory.get("last_observed_index", 0):]

    tail_budget = max(
        _MIN_TAIL_BUDGET,
        int(config["observation_threshold_tokens"] * _OBSERVATION_TAIL_RATIO),
    )
    split = split_by_tail_budget(unobserved, tail_budget, memory.get("calibration"))
    head = split["head"]
    to_observe = head if head else unobserved

    model = resolve_model_for_provider(config["observer_model"])
    observed = await run_observer(
        client,
        api_url,
        api_key,
        extra_headers,
        model,
        memory.get("active_observations", ""),
        to_observe,
    )

    if not observed.get("observations"):
        return

    prev_index = memory.get("last_observed_index", 0)
    existing = memory.get("active_observations", "")

    # Append new observations to existing ones
    if existing:
        memory["active_observations"] = f"{existing.strip()}\n\n{observed['observations'].strip()}"
    else:
        memory["active_observations"] = observed["observations"].strip()

    # Advance the sealed index
    memory["last_observed_index"] = (
        prev_index + len(head) if head else len(messages)
    )
    memory["observation_token_count"] = estimate_tokens(
        memory["active_observations"], memory.get("calibration")
    )

    sealed = memory["last_observed_index"] - prev_index
    log("memory", f"Sealed {sealed} messages (indices {prev_index}–{memory['last_observed_index'] - 1})")
    log("memory", f"Thread: {memory['last_observed_index']} sealed | {len(messages) - memory['last_observed_index']} active")

    memory["observer_log_seq"] = memory.get("observer_log_seq", 0) + 1
    await persist_observer_log({
        "session_id": session["id"],
        "sequence": memory["observer_log_seq"],
        "observations": observed["observations"],
        "tokens": estimate_tokens(observed["observations"], memory.get("calibration")),
        "messages_observed": len(to_observe),
        "generation": memory.get("generation_count", 0),
        "sealed_range": (prev_index, memory["last_observed_index"] - 1),
    })


async def run_reflection(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    session: dict,
    config: dict,
) -> None:
    """Compress the current observation memory via the reflector.

    Calls the reflector and replaces ``session["memory"]["active_observations"]``
    with the compressed result.  Updates token counts and generation counter.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        session: Session dict (mutated in place via ``session["memory"]``).
        config: MemoryConfig dict.
    """
    memory = session["memory"]
    log("memory", f"Reflecting ({memory.get('observation_token_count', 0)} > {config['reflection_threshold_tokens']})")

    model = resolve_model_for_provider(config["reflector_model"])
    reflected = await run_reflector(
        client,
        api_url,
        api_key,
        extra_headers,
        model,
        memory.get("active_observations", ""),
        config["reflection_target_tokens"],
        memory.get("calibration"),
    )

    memory["active_observations"] = reflected["observations"]
    memory["observation_token_count"] = reflected["token_count"]
    memory["_last_reflection_output_tokens"] = reflected["token_count"]
    memory["generation_count"] = memory.get("generation_count", 0) + 1

    memory["reflector_log_seq"] = memory.get("reflector_log_seq", 0) + 1
    await persist_reflector_log({
        "session_id": session["id"],
        "sequence": memory["reflector_log_seq"],
        "observations": reflected["observations"],
        "tokens": reflected["token_count"],
        "generation": memory["generation_count"],
        "compression_level": reflected["compression_level"],
    })
