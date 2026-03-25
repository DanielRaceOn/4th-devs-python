# -*- coding: utf-8 -*-

#   reflector.py

"""
### Description:
Reflector — compresses and reorganizes observations when they exceed the token budget.

Iterates through compression levels (0–2), making a Responses API call at each
level and stopping as soon as the result is within the target token budget.
The best result found (fewest tokens) is always returned, even if the target
was not reached.

Based on Mastra's Observational Memory system.
https://mastra.ai/blog/observational-memory

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/reflector.ts


"""

from typing import Optional

import httpx

from ..config import REFLECTOR_MAX_OUTPUT_TOKENS
from ..ai.tokens import estimate_tokens
from ..ai.response import get_response_message_text
from ..helpers.utils import extract_tag
from ..helpers.log import log
from .prompts import REFLECTOR_SYSTEM_PROMPT, REFLECTOR_COMPRESSION_LEVELS, build_reflector_prompt


async def run_reflector(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    model: str,
    observations: str,
    target_tokens: int,
    calibration: Optional[dict] = None,
) -> dict:
    """Compress observations to fit within *target_tokens*.

    Makes up to ``len(REFLECTOR_COMPRESSION_LEVELS)`` LLM calls, each with
    increasing aggressiveness.  Stops early if the target is reached.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers.
        model: Model identifier for the reflector call.
        observations: Current observation text to compress.
        target_tokens: Desired maximum token count for the result.
        calibration: Optional calibration state for adjusted token estimates.

    Returns:
        ReflectorResult dict with keys ``observations``, ``token_count``,
        ``raw``, ``compression_level``.
    """
    best_observations = observations
    best_tokens = estimate_tokens(observations, calibration)
    best_raw = observations
    best_level = -1

    log("reflector", f"Compressing observations ({best_tokens} → target {target_tokens} tokens)")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **extra_headers}

    for level, guidance in enumerate(REFLECTOR_COMPRESSION_LEVELS):
        payload = {
            "model": model,
            "instructions": REFLECTOR_SYSTEM_PROMPT,
            "input": build_reflector_prompt(observations, guidance),
            "temperature": 0,
            "max_output_tokens": REFLECTOR_MAX_OUTPUT_TOKENS,
            "store": False,
        }

        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        raw = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                raw += get_response_message_text(item) or ""

        compressed = extract_tag(raw, "observations") or raw.strip()
        if not compressed:
            continue

        tokens = estimate_tokens(compressed, calibration)
        if tokens < best_tokens:
            best_observations = compressed
            best_tokens = tokens
            best_raw = raw
            best_level = level

        if tokens <= target_tokens:
            log("reflector", f"Compressed to {tokens} tokens (level {level})")
            return {
                "observations": compressed,
                "token_count": tokens,
                "raw": raw,
                "compression_level": level,
            }

    log("reflector", f"Best: {best_tokens} tokens (level {best_level})")
    return {
        "observations": best_observations,
        "token_count": best_tokens,
        "raw": best_raw,
        "compression_level": best_level,
    }
