# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API wrapper — sends chat requests (with optional tools) to OpenAI or
OpenRouter and extracts tool calls, text, and reasoning summaries from the
response output array.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/api.js`

"""

from typing import Any

import httpx

from ..config import AI_API_KEY, RESPONSES_API_ENDPOINT, EXTRA_API_HEADERS, API
from .stats import record_usage


async def chat(
    *,
    model: str | None = None,
    input: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    reasoning: dict | None = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Send a request to the Responses API and return the parsed response.

    Uses the module-level API config as defaults; any argument overrides it.

    Args:
        model: Model identifier. Defaults to ``API['model']``.
        input: Message array (Responses API format).
        tools: Tool definitions to pass to the model.
        tool_choice: Tool selection strategy (default ``"auto"``).
        instructions: System prompt / instructions override.
        max_output_tokens: Token cap override.
        reasoning: Reasoning config dict, or ``None`` to omit.
            Pass the sentinel ``...`` (default) to use ``API['reasoning']``.

    Returns:
        Parsed JSON response dict from the API.

    Raises:
        RuntimeError: If the API returns an error field.
    """
    # Resolve defaults from module config
    _model = model if model is not None else API["model"]
    _instructions = instructions if instructions is not None else API["instructions"]
    _max_tokens = (
        max_output_tokens if max_output_tokens is not None else API["max_output_tokens"]
    )
    # Sentinel check: use API reasoning unless caller explicitly passed a value
    _reasoning = API["reasoning"] if reasoning is ... else reasoning

    body: dict[str, Any] = {"model": _model, "input": input}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if _instructions:
        body["instructions"] = _instructions
    if _max_tokens:
        body["max_output_tokens"] = _max_tokens
    if _reasoning is not None:
        body["reasoning"] = _reasoning

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=body,
        )
        data = resp.json()

    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: dict[str, Any]) -> list[dict]:
    """Extract function_call items from the response output array.

    Args:
        response: Full API response dict.

    Returns:
        List of function-call output items.
    """
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def extract_text(response: dict[str, Any]) -> str | None:
    """Extract the first text string from a message in the response output.

    Args:
        response: Full API response dict.

    Returns:
        Text content, or ``None`` if no message item is found.
    """
    message = next(
        (item for item in response.get("output", []) if item.get("type") == "message"),
        None,
    )
    if not message:
        return None
    content = message.get("content", [])
    return content[0].get("text") if content else None


def extract_reasoning(response: dict[str, Any]) -> list[str]:
    """Extract reasoning summary strings from the response output.

    Args:
        response: Full API response dict.

    Returns:
        List of reasoning summary text strings (may be empty).
    """
    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") == "reasoning":
            for summary in item.get("summary") or []:
                text = summary.get("text")
                if text:
                    texts.append(text)
    return texts
