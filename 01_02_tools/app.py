# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Minimal tool-use example: defines two tools (get_weather, send_email), runs a
tool-use loop against the Responses API, and prints the final answer.  The model
uses web search to look up the current weather, then calls send_email with the
result.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `app.js`, `helper.js`


"""

import asyncio
import json
from typing import Any, Dict, List

import httpx

# Project-level config (one directory up from this module)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    AI_API_KEY,
    EXTRA_API_HEADERS,
    RESPONSES_API_ENDPOINT,
    resolve_model_for_provider,
    AI_PROVIDER,
)
from helper import (
    build_next_conversation,
    get_final_text,
    get_tool_calls,
    log_answer,
    log_question,
)

# ---------------------------------------------------------------------------
# Step 1: Tool definitions (JSON Schema sent to the model)
# ---------------------------------------------------------------------------

MODEL = resolve_model_for_provider("gpt-4.1-mini")

# buildResponsesRequest() maps webSearch=True to OpenAI web_search_preview tool
# or OpenRouter :online model suffix.  We replicate that logic inline here.
WEB_SEARCH: bool = True

tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather for a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "send_email",
        "description": "Send a short email message to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Plain-text email body"},
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

# ---------------------------------------------------------------------------
# Step 2: Tool implementations (never sent to the model)
# ---------------------------------------------------------------------------


def _require_text(value: str, field_name: str) -> str:
    """Validate that *value* is a non-empty string.

    Args:
        value: The value to validate.
        field_name: Name used in the error message.

    Returns:
        Stripped string.

    Raises:
        ValueError: If *value* is not a non-empty string.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'"{field_name}" must be a non-empty string.')
    return value.strip()


handlers: Dict[str, Any] = {
    "get_weather": lambda args: {
        "Kraków": {"temp": -2, "conditions": "snow"},
        "London": {"temp": 8, "conditions": "rain"},
        "Tokyo": {"temp": 15, "conditions": "cloudy"},
    }.get(_require_text(args["location"], "location"), {"temp": None, "conditions": "unknown"}),
    "send_email": lambda args: {
        "success": True,
        "status": "sent",
        "to": _require_text(args["to"], "to"),
        "subject": _require_text(args["subject"], "subject"),
        "body": _require_text(args["body"], "body"),
    },
}

# ---------------------------------------------------------------------------
# Step 3: Responses API request builder (mirrors buildResponsesRequest)
# ---------------------------------------------------------------------------


def _build_request(
    model: str,
    input_: List[Dict[str, Any]],
    tool_list: List[Dict[str, Any]],
    web_search: bool,
) -> Dict[str, Any]:
    """Build the request body for the Responses API.

    Handles the provider-specific differences for enabling web search:
    - OpenAI: adds a ``web_search_preview`` tool entry.
    - OpenRouter: appends ``:online`` to the model name.

    Args:
        model: Resolved model identifier.
        input_: Conversation items list.
        tool_list: Tool definitions to send.
        web_search: Whether to enable web search.

    Returns:
        Dict ready to serialise as JSON request body.
    """
    body: Dict[str, Any] = {"model": model, "input": input_, "tools": tool_list}

    if web_search:
        if AI_PROVIDER == "openrouter":
            # Append :online suffix to enable native web search on OpenRouter
            if not body["model"].endswith(":online"):
                body["model"] = f"{body['model']}:online"
        else:
            # OpenAI: inject the built-in web_search_preview tool
            has_web_search = any(t.get("type") == "web_search_preview" for t in body["tools"])
            if not has_web_search:
                body["tools"] = [*body["tools"], {"type": "web_search_preview"}]

    return body


# ---------------------------------------------------------------------------
# Step 4: API call + tool-use loop
# ---------------------------------------------------------------------------

MAX_TOOL_STEPS = 5


async def _request_response(input_: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send *input_* to the Responses API and return the parsed response.

    Args:
        input_: Conversation items to send.

    Returns:
        Parsed JSON response dict.

    Raises:
        RuntimeError: If the API returns an error status or error payload.
    """
    body = _build_request(MODEL, input_, tools, WEB_SEARCH)

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
    if not response.is_success:
        message = (data.get("error") or {}).get("message") or f"Request failed ({response.status_code})"
        raise RuntimeError(message)
    return data


async def chat(conversation: List[Dict[str, Any]]) -> str:
    """Run the tool-use loop until the model provides a final text answer.

    This is a small tool-using workflow, not a full autonomous agent:

      USER question → model response → optional tool call(s) → tool result(s) → model response

    Args:
        conversation: Initial conversation (e.g. ``[{"role": "user", "content": "…"}]``).

    Returns:
        Final text answer from the model.

    Raises:
        RuntimeError: If the loop exceeds ``MAX_TOOL_STEPS`` without a final answer.
    """
    current = conversation
    for _ in range(MAX_TOOL_STEPS):
        response = await _request_response(current)
        calls = get_tool_calls(response)

        if not calls:
            return get_final_text(response)

        current = await build_next_conversation(current, calls, handlers)

    raise RuntimeError(f"Tool calling did not finish within {MAX_TOOL_STEPS} steps.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the weather-then-email demo query."""
    query = (
        "Use web search to check the current weather in Kraków. "
        "Then send a short email with the answer to student@example.com."
    )
    log_question(query)
    answer = await chat([{"role": "user", "content": query}])
    log_answer(answer)


if __name__ == "__main__":
    asyncio.run(main())
