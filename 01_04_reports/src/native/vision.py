# -*- coding: utf-8 -*-

#   vision.py

"""
### Description:
Vision API helper for quality analysis of generated images using the Responses API.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/vision.js

"""

import httpx

from ..config import API_CONFIG, AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT
from ..helpers.response import extract_response_text
from ..helpers.stats import record_usage


async def vision(
    *,
    image_base64: str,
    mime_type: str,
    question: str,
) -> str:
    """Analyse an image by sending it base64-encoded to the Responses API.

    Args:
        image_base64: Base64-encoded image data.
        mime_type: MIME type of the image (e.g. ``"image/jpeg"``).
        question: Prompt / question to ask about the image.

    Returns:
        Text answer from the model.

    Raises:
        Exception: If the API returns a non-success status or an error body.
    """
    body = {
        "model": API_CONFIG["vision_model"],
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": question},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}",
                    },
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
