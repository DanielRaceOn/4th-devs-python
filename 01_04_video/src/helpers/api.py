# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
OpenAI Responses API wrapper for the video processing agent. Provides chat(),
extract_tool_calls(), and extract_text() — the three functions used by agent.py.

Note: This module uses the Responses API (/v1/responses), which has a different
request/response format from the Chat Completions API (/v1/chat/completions):
- ``input`` (list) instead of ``messages``
- ``instructions`` instead of a system message item
- ``output`` array in the response (not ``choices``)

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/api.js`


"""

import logging
from typing import Any

import httpx

from ..config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT, api
from .stats import record_usage

logger = logging.getLogger(__name__)


async def chat(
    *,
    model: str | None = None,
    input: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    instructions: str | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Call the OpenAI Responses API.

    Args:
        model: Model override; defaults to ``api.model`` from config.
        input: List of message/tool-result items (the conversation history).
        tools: List of OpenAI function tool definitions, or ``None``.
        tool_choice: Tool selection strategy; default ``"auto"``.
        instructions: System instructions override; defaults to ``api.instructions``.
        max_output_tokens: Token limit override; defaults to ``api.max_output_tokens``.

    Returns:
        Raw API response dict containing ``output`` and ``usage``.

    Raises:
        RuntimeError: On API error or non-2xx response.
    """
    _model = model or api.model
    _instructions = instructions if instructions is not None else api.instructions
    _max_tokens = max_output_tokens or api.max_output_tokens

    body: dict[str, Any] = {"model": _model, "input": input}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if _instructions:
        body["instructions"] = _instructions
    if _max_tokens:
        body["max_output_tokens"] = _max_tokens

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
        **EXTRA_API_HEADERS,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT, headers=headers, json=body
        )

    data: dict[str, Any] = response.json()

    if not response.is_success or data.get("error"):
        err_msg = (
            (data.get("error") or {}).get("message")
            or f"Responses API request failed ({response.status_code})"
        )
        raise RuntimeError(err_msg)

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract function_call items from a Responses API response.

    Args:
        response: Raw API response dict.

    Returns:
        List of items where ``type == "function_call"``.
    """
    return [
        item
        for item in (response.get("output") or [])
        if item.get("type") == "function_call"
    ]


def extract_text(response: dict[str, Any]) -> str | None:
    """Extract the final text answer from a Responses API response.

    Checks ``output_text`` shorthand first, then walks ``output[].content[]``
    looking for ``output_text`` type parts.

    Args:
        response: Raw API response dict.

    Returns:
        Text string, or ``None`` if no text content found.
    """
    # Fast path: top-level output_text field
    if isinstance(response.get("output_text"), str) and response["output_text"].strip():
        return response["output_text"]

    # Walk output items of type "message", then their content parts
    messages = [
        item
        for item in (response.get("output") or [])
        if item.get("type") == "message"
    ]
    for message in messages:
        for part in message.get("content") or []:
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return part["text"]

    return None
