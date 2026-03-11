# -*- coding: utf-8 -*-

#   ai.py

"""
### Description:
AI provider client — calls the Responses API (OpenAI / OpenRouter).
Used by the agent loop to send queries and receive tool calls or text.
All parameters are passed explicitly by the caller.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/ai.js`

"""

import sys
from pathlib import Path
from typing import Any, Optional

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT

from .helpers.stats import record_usage


def _extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    output = data.get("output") or []
    message = next((o for o in output if o.get("type") == "message"), None)
    content = (message or {}).get("content") or []
    part = next((c for c in content if c.get("type") == "output_text"), None)
    return (part or {}).get("text", "").strip()


async def chat(
    *,
    model: str,
    input: list[dict],
    tools: Optional[list[dict]] = None,
    tool_choice: str = "auto",
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> dict:
    """Send a chat request to the Responses API.

    Args:
        model: Model identifier.
        input: Conversation messages.
        tools: Optional tool definitions.
        tool_choice: Tool selection strategy.
        instructions: System instructions.
        max_output_tokens: Optional token cap.

    Returns:
        Raw API response dict.

    Raises:
        RuntimeError: If the API call fails.
    """
    body: dict[str, Any] = {"model": model, "input": input}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if instructions:
        body["instructions"] = instructions
    if max_output_tokens:
        body["max_output_tokens"] = max_output_tokens

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
        **EXTRA_API_HEADERS,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            json=body,
            headers=headers,
            timeout=120.0,
        )

    data = response.json()

    if not response.is_success or data.get("error"):
        msg = (data.get("error") or {}).get("message") or f"API request failed ({response.status_code})"
        raise RuntimeError(msg)

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: dict) -> list[dict]:
    """Extract function call items from a Responses API output."""
    return [item for item in (response.get("output") or []) if item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract text from a Responses API response, or None if absent."""
    return _extract_response_text(response) or None
