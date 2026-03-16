# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API client for chat completions, tool support, and vision calls.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/api.js

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


async def vision(
    image_path: str,
    image_base64: str,
    mime_type: str,
    question: str,
) -> str:
    """Call a vision-capable model with an image and a question.

    Args:
        image_path: Path to the image (for logging purposes only).
        image_base64: Base64-encoded image data.
        mime_type: MIME type of the image (e.g. ``"image/jpeg"``).
        question: Question or analysis prompt to ask about the image.

    Returns:
        Response text string from the model.
    """
    image_url = f"data:{mime_type};base64,{image_base64}"

    body: dict = {
        "model": API_CONFIG["vision_model"],
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": question},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
    }

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
            or f"Vision request failed ({response.status_code})"
        )
        raise Exception(error_msg)

    record_usage(data.get("usage", {}))
    return extract_response_text(data) or "No response"


def extract_tool_calls(response: dict) -> list:
    """Extract function_call items from a Responses API output list."""
    output = response.get("output") or []
    return [item for item in output if isinstance(item, dict) and item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract the text response from a Responses API response."""
    return extract_response_text(response) or None
