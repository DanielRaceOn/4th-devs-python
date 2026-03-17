# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API wrapper for the hybrid RAG agent — sends chat requests with
tool definitions, records token usage, and extracts tool calls / text /
reasoning summaries from the response.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/helpers/api.js

"""

from typing import Any, Dict, List, Optional

import httpx

from ..config import AI_API_KEY, RESPONSES_API_ENDPOINT, EXTRA_API_HEADERS, API
from .stats import record_usage


async def chat(
    input_messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    model: Optional[str] = None,
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    reasoning: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a request to the Responses API and return the full response dict.

    Args:
        input_messages: Conversation history as a list of message dicts.
        tools: Optional list of tool definitions.
        tool_choice: Tool selection strategy (default ``"auto"``).
        model: Override model; defaults to ``API["model"]``.
        instructions: Override system instructions; defaults to ``API["instructions"]``.
        max_output_tokens: Override max output tokens; defaults to ``API["max_output_tokens"]``.
        reasoning: Override reasoning config; defaults to ``API["reasoning"]``.

    Returns:
        Full parsed JSON response dict.

    Raises:
        RuntimeError: If the API returns an error object.
    """
    body: Dict[str, Any] = {
        "model": model or API["model"],
        "input": input_messages,
    }

    _tools = tools or []
    if _tools:
        body["tools"] = _tools
        body["tool_choice"] = tool_choice

    _instructions = instructions or API["instructions"]
    if _instructions:
        body["instructions"] = _instructions

    _max_tokens = max_output_tokens or API["max_output_tokens"]
    if _max_tokens:
        body["max_output_tokens"] = _max_tokens

    _reasoning = reasoning or API.get("reasoning")
    if _reasoning:
        body["reasoning"] = _reasoning

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=body,
        )

    data: Dict[str, Any] = response.json()

    if data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(msg or str(err))

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all ``function_call`` items from the response output.

    Args:
        response: Full API response dict.

    Returns:
        List of function_call output items.
    """
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def extract_text(response: Dict[str, Any]) -> Optional[str]:
    """Extract the text from the first ``message`` item in the response output.

    Args:
        response: Full API response dict.

    Returns:
        Text string or None if no message is found.
    """
    for item in response.get("output", []):
        if item.get("type") == "message":
            content = item.get("content", [])
            if content:
                return content[0].get("text")
    return None


def extract_reasoning(response: Dict[str, Any]) -> List[str]:
    """Extract reasoning summary texts from the response output.

    Args:
        response: Full API response dict.

    Returns:
        List of reasoning summary text strings.
    """
    texts: List[str] = []
    for item in response.get("output", []):
        if item.get("type") == "reasoning":
            for summary in item.get("summary") or []:
                text = summary.get("text")
                if text:
                    texts.append(text)
    return texts
