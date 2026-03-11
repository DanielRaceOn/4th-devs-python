# -*- coding: utf-8 -*-

#   ai.py

"""
### Description:
AI provider client — calls the Responses API (OpenAI / OpenRouter).
Thin wrapper used by the sampling handler to generate LLM completions
on behalf of the MCP server.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/ai.js`

"""

import sys
from pathlib import Path
from typing import Any

import httpx

# Add project root to path so we can import the shared config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT


def _extract_text(data: dict) -> str:
    """Extract text from a Responses API response.

    The Responses API can return text in two places:
      1. data["output_text"]  — direct shorthand
      2. data["output"][]["content"][]["text"]  — nested message format
    """
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    output = data.get("output") or []
    message = next((o for o in output if o.get("type") == "message"), None)
    content = (message or {}).get("content") or []
    part = next((c for c in content if c.get("type") == "output_text"), None)
    return (part or {}).get("text", "").strip()


async def completion(
    *,
    model: str,
    input: list[dict],
    max_output_tokens: int | None = None,
) -> str:
    """Call the Responses API and return the generated text.

    Args:
        model: Model identifier, e.g. ``"gpt-5.1"``.
        input: List of message dicts in Responses API format.
        max_output_tokens: Optional token cap for the response.

    Returns:
        Stripped text output from the model.

    Raises:
        RuntimeError: If the API call fails or returns an empty response.
    """
    body: dict[str, Any] = {"model": model, "input": input}
    if max_output_tokens is not None:
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
            timeout=60.0,
        )

    data = response.json()

    if not response.is_success or data.get("error"):
        msg = (data.get("error") or {}).get("message") or f"API request failed ({response.status_code})"
        raise RuntimeError(msg)

    text = _extract_text(data)
    if not text:
        raise RuntimeError("Empty response")

    return text
