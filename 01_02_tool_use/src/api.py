# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Low-level Responses API client for 01_02_tool_use: sends a single chat turn
(with optional tools and instructions) and provides helpers to extract tool
calls and text from the response.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/api.js`


"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Add project root so the top-level config.py is importable from sub-packages.
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT


async def chat(
    *,
    model: str,
    input_: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """Send one conversation turn to the Responses API and return the response.

    Args:
        model: Resolved model identifier (e.g. ``"gpt-4.1"``).
        input_: List of conversation items (role/content dicts plus any
            function_call / function_call_output items from previous turns).
        tools: Optional list of tool definitions (JSON Schema dicts).
        tool_choice: How the model should select tools (default ``"auto"``).
        instructions: Optional system-level instructions prepended to the turn.

    Returns:
        Parsed JSON response dict from the API.

    Raises:
        RuntimeError: If the API returns a non-2xx status or an error payload.
    """
    body: Dict[str, Any] = {"model": model, "input": input_}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice

    if instructions:
        body["instructions"] = instructions

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            timeout=60.0,
        )

    data = response.json()

    if not response.is_success or data.get("error"):
        message = (data.get("error") or {}).get("message") or (
            f"Request failed with status {response.status_code}"
        )
        raise RuntimeError(message)

    return data


def extract_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return all function_call items from the Responses API output array.

    Args:
        response: Parsed Responses API response dict.

    Returns:
        List of function_call items (may be empty if the model gave a text reply).
    """
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def extract_text(response: Dict[str, Any]) -> Optional[str]:
    """Extract the assistant's text reply from a Responses API response.

    Tries the convenience ``output_text`` field first, then falls back to the
    first message item's content text.

    Args:
        response: Parsed Responses API response dict.

    Returns:
        Text string, or ``None`` if no text output was found.
    """
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response.get("output", []):
        if item.get("type") == "message":
            content = item.get("content", [])
            if content:
                return content[0].get("text")

    return None
