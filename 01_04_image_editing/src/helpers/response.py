# -*- coding: utf-8 -*-

#   response.py

"""
### Description:
Utility for extracting plain text from Responses API response objects.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/response.js

"""

from typing import Optional


def extract_response_text(data: dict) -> Optional[str]:
    """Extract the text content from a Responses API response dict.

    Checks ``output_text`` shortcut first, then walks ``output`` messages.

    Args:
        data: Raw Responses API response dictionary.

    Returns:
        Extracted text string, or ``None`` if not present.
    """
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    output = data.get("output") or []
    messages = [item for item in output if isinstance(item, dict) and item.get("type") == "message"]

    for message in messages:
        content = message.get("content") or []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    return text

    return None
