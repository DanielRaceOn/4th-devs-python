# -*- coding: utf-8 -*-

#   observer.py

"""
### Description:
Observer — extracts structured observations from conversation history.

Serializes unobserved messages into a plain-text block, sends them together
with any existing observations to an LLM call via the Responses API, then
parses the XML-structured output into an ObserverResult.

Based on Mastra's Observational Memory system.
https://mastra.ai/blog/observational-memory

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/observer.ts


"""

import httpx

from ..config import (
    OBSERVER_MAX_SECTION_CHARS,
    OBSERVER_MAX_TOOL_PAYLOAD_CHARS,
    OBSERVER_MAX_OUTPUT_TOKENS,
)
from ..ai.response import get_response_message_text
from ..ai.tokens import estimate_tokens_raw
from ..helpers.utils import truncate, extract_tag
from ..helpers.log import log
from ..types import is_text_message, is_function_call, is_function_call_output
from .prompts import OBSERVER_SYSTEM_PROMPT, build_observer_prompt


def serialize_messages(messages: list[dict]) -> str:
    """Render a message list as a human-readable string for the observer.

    Each message type gets a distinct heading and its content is truncated to
    prevent the observer prompt from growing unbounded.

    Args:
        messages: List of message dicts (TextMessage, FunctionCallItem, or
            FunctionCallOutputItem).

    Returns:
        Multi-section string separated by ``---`` dividers.
    """
    parts = []
    for i, msg in enumerate(messages):
        idx = i + 1

        if is_function_call_output(msg):
            parts.append(
                f"**Tool Result (#{idx}):**\n"
                f"{truncate(msg.get('output', ''), OBSERVER_MAX_TOOL_PAYLOAD_CHARS)}"
            )
        elif is_function_call(msg):
            parts.append(
                f"**Assistant Tool Call (#{idx}):**\n"
                f"[Tool: {msg.get('name', '')}] "
                f"{truncate(msg.get('arguments', ''), OBSERVER_MAX_TOOL_PAYLOAD_CHARS)}"
            )
        elif is_text_message(msg):
            role = msg.get("role", "")
            label = role[0].upper() + role[1:] if role else "Unknown"
            content = msg.get("content") or ""
            parts.append(
                f"**{label} (#{idx}):**\n"
                f"{truncate(content, OBSERVER_MAX_SECTION_CHARS) or '[empty]'}"
            )

    return "\n\n---\n\n".join(parts)


def parse_observer_output(raw: str) -> dict:
    """Parse the observer LLM output into an ObserverResult dict.

    Falls back to the raw text as observations if no ``<observations>`` tag is
    found.

    Args:
        raw: Raw LLM response text.

    Returns:
        ObserverResult dict with keys ``observations``, ``current_task``,
        ``suggested_response``, ``raw``.
    """
    return {
        "observations": extract_tag(raw, "observations") or raw.strip(),
        "current_task": extract_tag(raw, "current-task"),
        "suggested_response": extract_tag(raw, "suggested-response"),
        "raw": raw,
    }


async def run_observer(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    extra_headers: dict,
    model: str,
    previous_observations: str,
    messages: list[dict],
) -> dict:
    """Extract new observations from a batch of messages.

    Serializes *messages*, sends a Responses API call, and parses the output.
    Returns an empty result (no LLM call) when the serialized history is blank.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_url: Full URL of the Responses API endpoint.
        api_key: Bearer token for the API.
        extra_headers: Additional request headers (e.g. for OpenRouter).
        model: Model identifier for the observer call.
        previous_observations: Observations accumulated so far in this session.
        messages: New unobserved messages to process.

    Returns:
        ObserverResult dict.
    """
    history = serialize_messages(messages)
    if not history.strip():
        return {"observations": "", "raw": ""}

    log("observer", f"Extracting from {len(messages)} messages (~{estimate_tokens_raw(history)} tokens)")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **extra_headers}
    payload = {
        "model": model,
        "instructions": OBSERVER_SYSTEM_PROMPT,
        "input": build_observer_prompt(previous_observations, history),
        "temperature": 0.3,
        "max_output_tokens": OBSERVER_MAX_OUTPUT_TOKENS,
        "store": False,
    }

    response = await client.post(api_url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Extract text from all output message items
    raw = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            raw += get_response_message_text(item) or ""

    result = parse_observer_output(raw)
    line_count = len([l for l in result["observations"].split("\n") if l.strip()])
    log("observer", f"Extracted {line_count} observation lines (~{estimate_tokens_raw(result['observations'])} tokens)")

    return result
