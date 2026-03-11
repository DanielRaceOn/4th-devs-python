# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
AI provider client — calls the Responses API (OpenAI / OpenRouter).
Used by the agent loop to send queries and receive tool calls or text.
Pulls default model, instructions, and max_output_tokens from config.py.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/helpers/api.js`

"""

import sys
from pathlib import Path
from typing import Any, Optional

import httpx

# Root project config
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT

# Module-level config (imported from src/config.py via late import to avoid circular)
_src_config_path = Path(__file__).parent.parent

from .stats import record_usage


def _extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    messages = [item for item in (data.get("output") or []) if item.get("type") == "message"]
    for message in messages:
        for part in (message.get("content") or []):
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return part["text"]
    return ""


async def chat(
    *,
    model: Optional[str] = None,
    input: list[dict],
    tools: Optional[list[dict]] = None,
    tool_choice: str = "auto",
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> dict:
    """Call the Responses API.

    Args:
        model: Model identifier. Falls back to ``api.model`` from config.
        input: Conversation messages.
        tools: Optional tool definitions.
        tool_choice: Tool selection strategy.
        instructions: System instructions.
        max_output_tokens: Max tokens cap.

    Returns:
        Raw API response dict.

    Raises:
        RuntimeError: If the API call fails.
    """
    # Import config lazily to avoid circular imports at module load time
    from src.config import api as api_cfg

    resolved_model = model or api_cfg.model
    resolved_instructions = instructions if instructions is not None else api_cfg.instructions
    resolved_max = max_output_tokens or api_cfg.max_output_tokens

    body: dict[str, Any] = {"model": resolved_model, "input": input}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if resolved_instructions:
        body["instructions"] = resolved_instructions
    if resolved_max:
        body["max_output_tokens"] = resolved_max

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
        msg = (data.get("error") or {}).get("message") or f"Responses API request failed ({response.status_code})"
        raise RuntimeError(msg)

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: dict) -> list[dict]:
    """Extract function call items from a Responses API output."""
    return [item for item in (response.get("output") or []) if item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract text from a Responses API response, or None if absent."""
    return _extract_response_text(response) or None
