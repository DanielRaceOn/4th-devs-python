# -*- coding: utf-8 -*-

#   gemini.py

"""
### Description:
Image generation/editing wrapper supporting both OpenRouter and native Gemini backends.
Also provides process_video() for video analysis via Gemini GenerateContent API.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/gemini.js

"""

from typing import Optional

import httpx

from ..config import GEMINI_CONFIG, OPENROUTER_API_KEY, EXTRA_API_HEADERS
from ..helpers.stats import record_gemini
from ..helpers.logger import log


def _normalize_image_size(image_size: Optional[str]) -> Optional[str]:
    """Normalise image size string — uppercase trailing 'k' to 'K'."""
    if not isinstance(image_size, str):
        return image_size
    return image_size[:-1] + "K" if image_size.endswith("k") else image_size


def _build_image_config(options: dict) -> Optional[dict]:
    """Build image generation config dict from options."""
    image_config: dict = {}
    if options.get("aspectRatio"):
        image_config["aspect_ratio"] = options["aspectRatio"]
    if options.get("imageSize"):
        image_config["image_size"] = _normalize_image_size(options["imageSize"])
    return image_config if image_config else None


def _extract_native_text(interaction: dict) -> str:
    outputs = interaction.get("outputs") or []
    text_output = next((o for o in outputs if o.get("type") == "text"), None)
    return (text_output.get("text") or "").strip() if text_output else ""


def _extract_native_image(interaction: dict, action_label: str) -> dict:
    """Extract image data from a native Gemini Interactions API response."""
    outputs = interaction.get("outputs") or []
    image_output = next((o for o in outputs if o.get("type") == "image"), None)

    if not image_output:
        message = _extract_native_text(interaction)
        if message:
            raise Exception(f"{action_label} failed: {message}")
        raise Exception("No image output received from image backend")

    return {
        "data": image_output["data"],
        "mimeType": image_output.get("mime_type") or "image/png",
    }


def _extract_openrouter_text(data: dict) -> str:
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict):
            parts.append(part.get("text") or "")
    return "\n".join(parts).strip()


def _parse_data_url(data_url: str) -> dict:
    """Parse a base64 data URL into mimeType and raw base64 data."""
    import re
    match = re.match(r"^data:([^;]+);base64,(.+)$", data_url or "", re.DOTALL)
    if not match:
        raise Exception("Expected OpenRouter image output as a base64 data URL")
    return {"mimeType": match.group(1), "data": match.group(2)}


def _extract_openrouter_image(data: dict, action_label: str) -> dict:
    """Extract image data from an OpenRouter chat completion response."""
    images = ((data.get("choices") or [{}])[0].get("message", {}).get("images") or [])
    first = images[0] if images else {}
    image_url = (
        (first.get("image_url") or {}).get("url")
        or (first.get("imageUrl") or {}).get("url")
    )

    if not image_url:
        message = _extract_openrouter_text(data)
        if message:
            raise Exception(f"{action_label} failed: {message}")
        raise Exception("No image output received from OpenRouter")

    return _parse_data_url(image_url)


async def _create_native_interaction(
    prompt: str,
    reference_images: list,
    image_config: Optional[dict],
) -> dict:
    """Send an image generation request to the native Gemini Interactions API."""
    if reference_images:
        input_payload = [
            {"type": "text", "text": prompt},
            *[
                {"type": "image", "data": img["data"], "mime_type": img["mimeType"]}
                for img in reference_images
            ],
        ]
    else:
        input_payload = prompt

    payload: dict = {
        "model": GEMINI_CONFIG["image_model"],
        "input": input_payload,
        "response_modalities": ["IMAGE"],
    }

    if image_config:
        payload["generation_config"] = {"image_config": image_config}

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            GEMINI_CONFIG["endpoint"],
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
            },
            json=payload,
        )
        data = response.json()

    if not response.is_success or data.get("error"):
        raise Exception(
            (data.get("error") or {}).get("message")
            or f"Gemini image request failed ({response.status_code})"
        )

    return data


async def _create_openrouter_interaction(
    prompt: str,
    reference_images: list,
    image_config: Optional[dict],
) -> dict:
    """Send an image generation request via the OpenRouter chat completions API."""
    if reference_images:
        content: list = [
            {"type": "text", "text": prompt},
            *[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['mimeType']};base64,{img['data']}"},
                }
                for img in reference_images
            ],
        ]
    else:
        content = prompt  # type: ignore[assignment]

    body: dict = {
        "model": GEMINI_CONFIG["image_model"],
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }
    if image_config:
        body["image_config"] = image_config

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            GEMINI_CONFIG["openrouter_endpoint"],
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=body,
        )
        data = response.json()

    if not response.is_success or data.get("error"):
        raise Exception(
            (data.get("error") or {}).get("message")
            or f"OpenRouter image request failed ({response.status_code})"
        )

    return data


async def _request_image(
    *,
    prompt: str,
    reference_images: Optional[list] = None,
    options: Optional[dict] = None,
    log_action: str,
    success_label: str,
    stats_type: str,
    failure_label: str,
) -> dict:
    """Core image request dispatcher — logs, calls the active backend, records stats."""
    refs = reference_images or []
    opts = options or {}

    preview = prompt[:100] if not refs else f"{len(refs)} images"
    log.gemini(log_action, preview)

    image_config = _build_image_config(opts)

    if GEMINI_CONFIG["image_backend"] == "openrouter":
        response = await _create_openrouter_interaction(prompt, refs, image_config)
        image = _extract_openrouter_image(response, failure_label)
    else:
        response = await _create_native_interaction(prompt, refs, image_config)
        image = _extract_native_image(response, failure_label)

    record_gemini(stats_type)
    log.gemini_result(True, f"{success_label} ({image['mimeType']})")
    return image


async def generate_image(prompt: str, options: Optional[dict] = None) -> dict:
    """Generate a new image from a text prompt.

    Args:
        prompt: Textual description of the image to generate.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64) and ``mimeType``.
    """
    return await _request_image(
        prompt=prompt,
        options=options,
        log_action="Generating image",
        success_label="Generated image",
        stats_type="generate",
        failure_label="Image generation",
    )


async def edit_image(
    instructions: str,
    image_base64: str,
    mime_type: str,
    options: Optional[dict] = None,
) -> dict:
    """Edit a single reference image according to instructions.

    Args:
        instructions: Editing instructions / new prompt.
        image_base64: Base64-encoded source image.
        mime_type: MIME type of the source image.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64) and ``mimeType``.
    """
    return await _request_image(
        prompt=instructions,
        reference_images=[{"data": image_base64, "mimeType": mime_type}],
        options=options,
        log_action="Editing image",
        success_label="Edited image",
        stats_type="edit",
        failure_label="Image editing",
    )


async def edit_image_with_references(
    instructions: str,
    reference_images: list,
    options: Optional[dict] = None,
) -> dict:
    """Edit multiple reference images according to instructions.

    Args:
        instructions: Editing instructions / new prompt.
        reference_images: List of ``{data, mimeType}`` source image dicts.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64) and ``mimeType``.
    """
    return await _request_image(
        prompt=instructions,
        reference_images=reference_images,
        options=options,
        log_action="Editing with references",
        success_label="Generated image with references",
        stats_type="edit",
        failure_label="Image editing",
    )


async def process_video(video_base64: str, mime_type: str, prompt: str) -> str:
    """Analyze a video using Gemini's GenerateContent API.

    Requires GEMINI_API_KEY — video analysis always goes through native Gemini
    even when OpenRouter is used for image generation.

    Args:
        video_base64: Base64-encoded video data.
        mime_type: Video MIME type (e.g. ``"video/mp4"``).
        prompt: Analysis instructions.

    Returns:
        Analysis text from Gemini.

    Raises:
        Exception: If GEMINI_API_KEY is not set or Gemini returns an error.
    """
    if not GEMINI_CONFIG.get("api_key"):
        raise Exception(
            "GEMINI_API_KEY is required for native video analysis in this example"
        )

    log.gemini("Analyzing video", prompt[:80])

    video_endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_CONFIG['video_model']}:generateContent"
    )

    body: dict = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": video_base64}},
                    {"text": prompt},
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            video_endpoint,
            headers={
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
                "Content-Type": "application/json",
            },
            json=body,
        )
        data = response.json()

    if data.get("error"):
        raise Exception(data["error"].get("message") or str(data["error"]))

    record_gemini("analyze_video")

    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text")
    )

    if not text:
        raise Exception("No text response from Gemini")

    log.gemini_result(True, f"Video analyzed ({len(text)} chars)")
    return text
