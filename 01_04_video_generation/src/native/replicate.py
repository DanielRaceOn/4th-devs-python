# -*- coding: utf-8 -*-

#   replicate.py

"""
### Description:
Replicate API wrapper for Kling video generation (text-to-video and image-to-video).
Uses the kwaivgi/kling-v2.5-turbo-pro model via the replicate Python package.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/replicate.js

"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from ..helpers.logger import log

_PROJECT_ROOT = Path(__file__).parent.parent.parent

KLING_MODEL = "kwaivgi/kling-v2.5-turbo-pro"


def _get_replicate_client():
    """Lazy-import and return a Replicate client instance."""
    try:
        import replicate
        return replicate
    except ImportError:
        raise ImportError(
            "replicate package is not installed. "
            "Run: .venv/Scripts/python -m pip install replicate"
        )


async def generate_video(
    prompt: str,
    duration: int = 10,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
) -> dict:
    """Generate a video from a text prompt using Kling AI.

    Args:
        prompt: Text description of the video scene.
        duration: Duration in seconds (5 or 10).
        aspect_ratio: Aspect ratio — "16:9", "9:16", or "1:1".
        negative_prompt: Things to avoid in the video.

    Returns:
        Dict with ``url`` (video URL), ``prompt``, ``duration``, ``aspect_ratio``.
    """
    log.gemini("Generating video (Kling)", f"{duration}s - {prompt[:50]}...")

    replicate = _get_replicate_client()

    input_data = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "negative_prompt": negative_prompt,
    }

    try:
        # replicate.run is synchronous — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: replicate.run(KLING_MODEL, input=input_data),
        )

        # Output may be a FileOutput object with .url property or a plain URL string
        if hasattr(output, "url"):
            video_url = str(output.url)
        else:
            video_url = str(output)

        log.gemini_result(True, f"Video generated: {video_url}")

        return {
            "url": video_url,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
    except Exception as e:
        log.error("generate_video", str(e))
        raise


async def image_to_video(
    prompt: str,
    start_image_path: str,
    end_image_path: Optional[str] = None,
    duration: int = 10,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
) -> dict:
    """Generate a video from a start frame (and optional end frame) using Kling AI.

    Args:
        prompt: Description of motion and action to animate.
        start_image_path: Path to start frame relative to project root.
        end_image_path: Optional path to end frame relative to project root.
        duration: Duration in seconds (5 or 10).
        aspect_ratio: Aspect ratio — used when no start_image is provided.
        negative_prompt: Things to avoid in the video.

    Returns:
        Dict with ``url``, ``prompt``, ``duration``, ``start_image``, ``end_image``.
    """
    log.gemini("Image-to-video (Kling)", f"{duration}s from {start_image_path}")

    replicate = _get_replicate_client()

    # Read start image bytes
    start_full_path = _PROJECT_ROOT / start_image_path
    start_image_bytes = start_full_path.read_bytes()

    input_data: dict = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "negative_prompt": negative_prompt,
        "start_image": start_image_bytes,
    }

    if end_image_path:
        end_full_path = _PROJECT_ROOT / end_image_path
        input_data["end_image"] = end_full_path.read_bytes()

    try:
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: replicate.run(KLING_MODEL, input=input_data),
        )

        if hasattr(output, "url"):
            video_url = str(output.url)
        else:
            video_url = str(output)

        log.gemini_result(True, f"Video generated from image: {video_url}")

        return {
            "url": video_url,
            "prompt": prompt,
            "duration": duration,
            "start_image": start_image_path,
            "end_image": end_image_path or None,
        }
    except Exception as e:
        log.error("image_to_video", str(e))
        raise


async def download_video(url: str, output_name: str) -> str:
    """Download a video from URL and save to workspace/output/.

    Args:
        url: Video URL to download.
        output_name: Base name for the output file (without extension).

    Returns:
        Relative path to the saved video file.
    """
    log.info(f"Downloading video: {output_name}")

    output_dir = _PROJECT_ROOT / "workspace" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = int(datetime.now().timestamp() * 1000)
    filename = f"{output_name}_{ts}.mp4"
    output_path = output_dir / filename

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(url)
        if not response.is_success:
            raise Exception(f"Failed to download video: {response.status_code} {response.reason_phrase}")
        output_path.write_bytes(response.content)

    relative_path = f"workspace/output/{filename}"
    log.success(f"Video saved: {relative_path}")
    return relative_path
