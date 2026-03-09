# -*- coding: utf-8 -*-

#   helpers.py

"""
### Description:
Utility helpers for extracting text from Responses API responses and
building typed message dicts.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `helpers.js`

"""

from typing import Any


def extract_response_text(data: dict[str, Any]) -> str:
    """Return the output text from a Responses API response.

    Tries ``output_text`` first, then walks ``output`` for message parts.

    Args:
        data: Parsed JSON response from the Responses API.

    Returns:
        The first output text string found, or an empty string.
    """
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = data.get("output")
    messages = [item for item in (output or []) if item.get("type") == "message"]

    for message in messages:
        content = message.get("content") if isinstance(message.get("content"), list) else []
        for part in content:
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return part["text"]

    return ""


def to_message(role: str, content: str) -> dict[str, str]:
    """Build a Responses API message dict.

    Args:
        role: Message role, e.g. ``'user'`` or ``'assistant'``.
        content: Text content of the message.

    Returns:
        Dict with ``type``, ``role``, and ``content`` keys.
    """
    return {"type": "message", "role": role, "content": content}
