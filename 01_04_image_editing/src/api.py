# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API client for chat completions with tool support.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/api.js

"""

from typing import Optional

import httpx

from .config import API_CONFIG, AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT
from .helpers.response import extract_response_text
from .helpers.stats import record_usage


async def chat(
    model: str = API_CONFIG["model"],
    input_messages: Optional[list] = None,
    tools: Optional[list] = None,
    tool_choice: str = "auto",
    instructions: str = API_CONFIG["instructions"],
    max_output_tokens: int = API_CONFIG["max_output_tokens"],
) -> dict:
    """Call the Responses API for a chat completion.

    Args:
        model: Model identifier to use.
        input_messages: List of message dicts to send.
        tools: Tool definitions available to the model.
        tool_choice: Tool selection strategy, default ``"auto"``.
        instructions: System-level instructions for the model.
        max_output_tokens: Maximum number of tokens in the response.

    Returns:
        Raw API response dictionary.

    Raises:
        Exception: If the API returns a non-success status or an error body.
    """
    body: dict = {"model": model, "input": input_messages or []}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if instructions:
        body["instructions"] = instructions
    if max_output_tokens:
        body["max_output_tokens"] = max_output_tokens

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=body,
        )
        data = response.json()

    if not response.is_success or data.get("error"):
        error_msg = (
            (data.get("error") or {}).get("message")
            or f"Responses API request failed ({response.status_code})"
        )
        raise Exception(error_msg)

    record_usage(data.get("usage", {}))
    return data


def extract_tool_calls(response: dict) -> list:
    """Extract function_call items from a Responses API output list.

    Args:
        response: Raw API response dictionary.

    Returns:
        List of function_call dicts.
    """
    output = response.get("output") or []
    return [item for item in output if isinstance(item, dict) and item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract the text response from a Responses API response.

    Args:
        response: Raw API response dictionary.

    Returns:
        Response text string, or ``None`` if not present.
    """
    return extract_response_text(response) or None
