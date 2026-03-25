# -*- coding: utf-8 -*-

#   response.py

"""
### Description:
Helpers for parsing OpenAI Responses API output items.

The Responses API returns an ``output`` list containing message items and
function-call items.  This module provides type definitions (as plain dicts)
and a helper that extracts plain text from a message item's content array.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/ai/response.ts


"""


def get_response_message_text(message: dict) -> str:
    """Extract concatenated output text from a Responses API message item.

    A message item has ``type == "message"`` and a ``content`` list of
    content parts.  Only parts with ``type == "output_text"`` carry text.

    Args:
        message: A Responses API output item of type ``"message"``.

    Returns:
        Concatenated text from all ``output_text`` content parts.
    """
    text = ""
    for part in message.get("content", []):
        if part.get("type") == "output_text" and part.get("text"):
            text += part["text"]
    return text
