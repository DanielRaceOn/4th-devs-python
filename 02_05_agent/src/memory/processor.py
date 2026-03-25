# -*- coding: utf-8 -*-

#   processor.py

"""
### Description:
Memory processor — orchestrates the observer/reflector cycle.

Main entry point called before each Responses API call in the agent loop.

Context window layout:
┌──────────────────────────────────────────────────────┐
│  Observations (system prompt)  │  Unobserved tail    │
│  Compressed history            │  Raw recent messages │
└──────────────────────────────────────────────────────┘

Decision logic:
  1. Below threshold → passthrough (observations injected if they exist)
  2. Above threshold → observer seals head, keeps tail
  3. Observations too large → reflector compresses

Observer runs at most once per HTTP request (flag on ``session["memory"]``).

Based on Mastra's Observational Memory system.
https://mastra.ai/blog/observational-memory

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/processor.ts


"""

import httpx

from ..config import DEFAULT_MEMORY_CONFIG
from ..ai.tokens import estimate_messages_tokens_raw
from ..helpers.log import log, log_error
from .context import build_observed_context, build_passthrough_context
from .runtime import run_observation, run_reflection


async def process_memory(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    session: dict,
    base_system_prompt: str,
    config: dict | None = None,
) -> dict:
    """Decide whether to observe/reflect, then build the context for the LLM call.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        session: Session dict (may be mutated via ``session["memory"]``).
        base_system_prompt: Agent base system prompt.
        config: MemoryConfig dict.  Defaults to ``DEFAULT_MEMORY_CONFIG``.

    Returns:
        ProcessedContext dict with ``system_prompt`` and ``messages``.
    """
    if config is None:
        config = DEFAULT_MEMORY_CONFIG

    messages = session["messages"]
    memory = session["memory"]
    unobserved = messages[memory.get("last_observed_index", 0):]
    pending_tokens = estimate_messages_tokens_raw(unobserved)

    log(
        "memory",
        f"Pending: {pending_tokens} tokens ({len(unobserved)} msgs) | "
        f"Observations: {memory.get('observation_token_count', 0)} tokens "
        f"(gen {memory.get('generation_count', 0)})",
    )

    if pending_tokens < config["observation_threshold_tokens"]:
        return build_passthrough_context(session, base_system_prompt)

    if memory.get("_observer_ran_this_request"):
        log("memory", "Observer already ran this request, skipping")
        return build_passthrough_context(session, base_system_prompt)

    log("memory", f"Threshold exceeded ({pending_tokens} >= {config['observation_threshold_tokens']}), running observer")

    try:
        await run_observation(client, api_url, api_key, extra_headers, session, config)
        memory["_observer_ran_this_request"] = True
    except Exception as err:
        log_error("memory", "Observer failed:", err)
        return {"system_prompt": base_system_prompt, "messages": messages}

    obs_tokens = memory.get("observation_token_count", 0)
    last_reflection = memory.get("_last_reflection_output_tokens", 0)
    grew_since_reflection = obs_tokens - last_reflection
    should_reflect = (
        obs_tokens > config["reflection_threshold_tokens"]
        and grew_since_reflection >= config["reflection_target_tokens"]
    )

    if should_reflect:
        try:
            await run_reflection(client, api_url, api_key, extra_headers, session, config)
        except Exception as err:
            log_error("memory", "Reflector failed:", err)
    elif obs_tokens > config["reflection_threshold_tokens"]:
        log(
            "memory",
            f"Skipping reflection (grew {grew_since_reflection} tokens since last, need {config['reflection_target_tokens']})",
        )

    context = build_observed_context(session, base_system_prompt)
    log(
        "memory",
        f"Context: {len(context['messages'])} active msgs + observations "
        f"(gen {memory.get('generation_count', 0)}) | {memory.get('last_observed_index', 0)} sealed",
    )
    return context


async def flush_memory(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    session: dict,
    config: dict | None = None,
) -> None:
    """Force-observe all remaining unobserved messages (e.g. at session/demo end).

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        session: Session dict (mutated in place).
        config: MemoryConfig dict.  Defaults to ``DEFAULT_MEMORY_CONFIG``.
    """
    if config is None:
        config = DEFAULT_MEMORY_CONFIG

    messages = session["messages"]
    memory = session["memory"]
    unobserved = messages[memory.get("last_observed_index", 0):]
    if not unobserved:
        return

    log("flush", f"Observing {len(unobserved)} remaining messages")

    await run_observation(client, api_url, api_key, extra_headers, session, config)

    if memory.get("observation_token_count", 0) > config["reflection_threshold_tokens"]:
        try:
            await run_reflection(client, api_url, api_key, extra_headers, session, config)
        except Exception as err:
            log_error("flush", "Reflector failed:", err)
