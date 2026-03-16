# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions and handlers for video generation agent.
Tools: create_image, analyze_image, generate_video, image_to_video, analyze_video.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/tools.js

"""

import base64
from pathlib import Path
from typing import Any, Optional

from .gemini import (
    generate_image,
    edit_image,
    edit_image_with_references,
    process_video,
)
from .replicate import (
    generate_video as kling_generate_video,
    image_to_video as kling_image_to_video,
    download_video,
)
from ..api import vision
from ..helpers.logger import log

_PROJECT_ROOT = Path(__file__).parent.parent.parent

# MIME type mapping for common image formats
_IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Extension mapping for MIME types
_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _get_mime_type(file_path: str) -> str:
    """Return MIME type for an image file path based on extension."""
    ext = Path(file_path).suffix.lower()
    return _IMAGE_MIME_TYPES.get(ext, "image/png")


def _get_extension(mime_type: str) -> str:
    """Return file extension for a given MIME type."""
    return _IMAGE_EXTENSIONS.get(mime_type, ".png")


def _generate_filename(prefix: str, mime_type: str) -> str:
    """Generate a timestamped filename for an output image."""
    from datetime import datetime
    ts = int(datetime.now().timestamp() * 1000)
    ext = _get_extension(mime_type)
    return f"{prefix}_{ts}{ext}"


# ---------------------------------------------------------------------------
# Tool schema definitions (OpenAI function format)
# ---------------------------------------------------------------------------

native_tools = [
    {
        "type": "function",
        "name": "create_image",
        "description": (
            "Generate or edit images using Gemini. Use for creating video frames. "
            "If reference_images is empty, generates from prompt. "
            "If reference_images provided, edits/combines them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Description of image to generate. For best results, "
                        "pass the complete JSON template content as the prompt."
                    ),
                },
                "output_name": {
                    "type": "string",
                    "description": "Base name for the output file (without extension). Saved to workspace/output/",
                },
                "reference_images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional paths to reference image(s) for editing. Empty array = generate from scratch.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                    "description": "Aspect ratio of the output image. Default is 16:9 for video frames.",
                },
                "image_size": {
                    "type": "string",
                    "enum": ["1k", "2k", "4k"],
                    "description": "Resolution of the output image. Default is 2k",
                },
            },
            "required": ["prompt", "output_name", "reference_images"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "analyze_image",
        "description": (
            "Analyze a generated image for quality issues before using it as a video frame. "
            "Checks for prompt adherence, visual artifacts, style consistency."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file relative to the project root",
                },
                "original_prompt": {
                    "type": "string",
                    "description": "The original prompt or description used to generate the image",
                },
                "check_aspects": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "prompt_adherence",
                            "visual_artifacts",
                            "anatomy",
                            "text_rendering",
                            "style_consistency",
                            "composition",
                        ],
                    },
                    "description": "Specific aspects to check. If not provided, checks all aspects.",
                },
            },
            "required": ["image_path", "original_prompt"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "generate_video",
        "description": (
            "Generate a video from a text prompt using Kling AI. "
            "Creates a 10-second video by default. Use this when you don't have a start frame."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the video scene, motion, and action.",
                },
                "output_name": {
                    "type": "string",
                    "description": "Base name for the output video file (saved to workspace/output/)",
                },
                "duration": {
                    "type": "number",
                    "enum": [5, 10],
                    "description": "Video duration in seconds. Default: 10",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1"],
                    "description": "Video aspect ratio. Default: 16:9",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Things to avoid in the video (e.g., 'blurry, distorted, text')",
                },
            },
            "required": ["prompt", "output_name"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "image_to_video",
        "description": (
            "Generate a video from a start frame image using Kling AI. "
            "Use this when you have already created a start frame with create_image. "
            "Optionally provide an end frame for more control."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of motion and action to animate from the start frame.",
                },
                "start_image": {
                    "type": "string",
                    "description": "Path to the start frame image (e.g., workspace/output/frame_start.png)",
                },
                "end_image": {
                    "type": "string",
                    "description": "Optional path to the end frame image for controlled transitions",
                },
                "output_name": {
                    "type": "string",
                    "description": "Base name for the output video file (saved to workspace/output/)",
                },
                "duration": {
                    "type": "number",
                    "enum": [5, 10],
                    "description": "Video duration in seconds. Default: 10",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Things to avoid in the video",
                },
            },
            "required": ["prompt", "start_image", "output_name"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "analyze_video",
        "description": (
            "Analyze a generated video for quality, motion, and content. "
            "Use to review videos before delivering to user."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file relative to project root",
                },
                "analysis_focus": {
                    "type": "string",
                    "enum": ["general", "motion", "quality", "prompt_adherence"],
                    "description": "What to focus on in the analysis.",
                },
                "original_prompt": {
                    "type": "string",
                    "description": "The original prompt used to generate the video (for prompt_adherence check)",
                },
            },
            "required": ["video_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]

# ---------------------------------------------------------------------------
# Analysis prompts for analyze_video
# ---------------------------------------------------------------------------

_VIDEO_ANALYSIS_PROMPTS = {
    "general": """Analyze this video comprehensively. Describe:
- Overall content and what's happening
- Visual quality (resolution, artifacts, consistency)
- Motion quality (smoothness, naturalness)
- Key moments with timestamps
- Overall assessment""",

    "motion": """Analyze the motion quality in this video:
- Smoothness of movement
- Natural vs artificial motion
- Any jitter, stuttering, or unnatural transitions
- How well objects/subjects maintain consistency
- Motion artifacts or distortions""",

    "quality": """Analyze the visual quality of this video:
- Resolution and clarity
- Color consistency
- Artifacts or glitches
- Frame-to-frame consistency
- Overall production quality""",
}

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def _create_image_handler(
    prompt: str,
    output_name: str,
    reference_images: list,
    aspect_ratio: str = "16:9",
    image_size: str = "2k",
) -> dict:
    """Handle create_image tool call."""
    is_editing = bool(reference_images)
    mode = "edit" if is_editing else "generate"

    log.tool("create_image", {
        "mode": mode,
        "prompt": prompt[:50] + "...",
        "output_name": output_name,
        "references": len(reference_images),
    })

    try:
        options = {"aspectRatio": aspect_ratio, "imageSize": image_size}

        if is_editing:
            # Load reference images as base64
            loaded_images = []
            for image_path in reference_images:
                full_path = _PROJECT_ROOT / image_path
                image_bytes = full_path.read_bytes()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                mime_type = _get_mime_type(image_path)
                loaded_images.append({"data": image_base64, "mimeType": mime_type})

            if len(loaded_images) == 1:
                result = await edit_image(
                    prompt,
                    loaded_images[0]["data"],
                    loaded_images[0]["mimeType"],
                    options,
                )
            else:
                result = await edit_image_with_references(prompt, loaded_images, options)
        else:
            result = await generate_image(prompt, options)

        output_dir = _PROJECT_ROOT / "workspace" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = _generate_filename(output_name, result["mimeType"])
        output_path = output_dir / filename
        output_path.write_bytes(base64.b64decode(result["data"]))

        relative_path = f"workspace/output/{filename}"
        log.success(f"Image saved: {relative_path}")

        return {
            "success": True,
            "mode": mode,
            "output_path": relative_path,
            "absolute_path": str(output_path),
            "project_root": str(_PROJECT_ROOT),
            "mime_type": result["mimeType"],
            "prompt_used": prompt[:200] + ("..." if len(prompt) > 200 else ""),
        }
    except Exception as e:
        log.error("create_image", str(e))
        return {"success": False, "error": str(e)}


async def _analyze_image_handler(
    image_path: str,
    original_prompt: str,
    check_aspects: Optional[list] = None,
) -> dict:
    """Handle analyze_image tool call."""
    log.tool("analyze_image", {"image_path": image_path})

    try:
        full_path = _PROJECT_ROOT / image_path
        image_bytes = full_path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = _get_mime_type(image_path)

        aspects = check_aspects or [
            "prompt_adherence",
            "visual_artifacts",
            "style_consistency",
            "composition",
        ]

        prompt_lines = [
            f'Analyze this AI-generated image for use as a video frame. The original prompt was:\n"{original_prompt}"\n\nPlease evaluate:'
        ]
        if "prompt_adherence" in aspects:
            prompt_lines.append("1. PROMPT ADHERENCE: Does the image match what was requested?")
        if "visual_artifacts" in aspects:
            prompt_lines.append("2. VISUAL ARTIFACTS: Any glitches, distortions, or unnatural patterns?")
        if "style_consistency" in aspects:
            prompt_lines.append("3. STYLE: Is the visual style coherent?")
        if "composition" in aspects:
            prompt_lines.append("4. COMPOSITION: Is framing suitable for video animation?")

        prompt_lines.append(
            "\nProvide:\n"
            "- Quality score (1-10)\n"
            "- Issues found\n"
            "- Whether it's suitable as a video frame\n"
            "- Suggestions if regeneration needed"
        )
        analysis_prompt = "\n".join(prompt_lines)

        log.vision(image_path, "Frame quality analysis")

        analysis = await vision(
            image_path=image_path,
            image_base64=image_base64,
            mime_type=mime_type,
            question=analysis_prompt,
        )

        log.vision_result(analysis[:150])

        return {
            "success": True,
            "image_path": image_path,
            "aspects_checked": aspects,
            "analysis": analysis,
        }
    except Exception as e:
        log.error("analyze_image", str(e))
        return {"success": False, "error": str(e)}


async def _generate_video_handler(
    prompt: str,
    output_name: str,
    duration: int = 10,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
) -> dict:
    """Handle generate_video tool call."""
    log.tool("generate_video", {"prompt": prompt[:50] + "...", "duration": duration, "aspect_ratio": aspect_ratio})

    try:
        result = await kling_generate_video(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
        )

        local_path = await download_video(result["url"], output_name)

        return {
            "success": True,
            "output_path": local_path,
            "video_url": result["url"],
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
    except Exception as e:
        log.error("generate_video", str(e))
        return {"success": False, "error": str(e)}


async def _image_to_video_handler(
    prompt: str,
    start_image: str,
    output_name: str,
    end_image: Optional[str] = None,
    duration: int = 10,
    negative_prompt: str = "",
) -> dict:
    """Handle image_to_video tool call."""
    log.tool("image_to_video", {"start_image": start_image, "end_image": end_image or "none", "duration": duration})

    try:
        result = await kling_image_to_video(
            prompt=prompt,
            start_image_path=start_image,
            end_image_path=end_image,
            duration=duration,
            negative_prompt=negative_prompt,
        )

        local_path = await download_video(result["url"], output_name)

        return {
            "success": True,
            "output_path": local_path,
            "video_url": result["url"],
            "prompt": prompt,
            "start_image": start_image,
            "end_image": end_image or None,
            "duration": duration,
        }
    except Exception as e:
        log.error("image_to_video", str(e))
        return {"success": False, "error": str(e)}


async def _analyze_video_handler(
    video_path: str,
    analysis_focus: str = "general",
    original_prompt: Optional[str] = None,
) -> dict:
    """Handle analyze_video tool call."""
    log.tool("analyze_video", {"video_path": video_path, "analysis_focus": analysis_focus})

    try:
        full_path = _PROJECT_ROOT / video_path
        video_bytes = full_path.read_bytes()
        video_base64 = base64.b64encode(video_bytes).decode("utf-8")

        if analysis_focus == "prompt_adherence" and original_prompt:
            prompt = (
                f'The video was generated with this prompt: "{original_prompt}"\n\n'
                "Analyze how well the video matches the prompt:\n"
                "- Which elements from the prompt are present?\n"
                "- What's missing or different?\n"
                "- How accurate is the motion/action?\n"
                "- Overall adherence score (1-10)"
            )
        else:
            prompt = _VIDEO_ANALYSIS_PROMPTS.get(
                analysis_focus, _VIDEO_ANALYSIS_PROMPTS["general"]
            )

        analysis = await process_video(
            video_base64=video_base64,
            mime_type="video/mp4",
            prompt=prompt,
        )

        log.success(f"Video analyzed ({analysis_focus})")

        return {
            "success": True,
            "video_path": video_path,
            "analysis_focus": analysis_focus,
            "analysis": analysis,
        }
    except Exception as e:
        log.error("analyze_video", str(e))
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_native_handlers = {
    "create_image": _create_image_handler,
    "analyze_image": _analyze_image_handler,
    "generate_video": _generate_video_handler,
    "image_to_video": _image_to_video_handler,
    "analyze_video": _analyze_video_handler,
}


def is_native_tool(name: str) -> bool:
    """Return True if name is a registered native tool."""
    return name in _native_handlers


async def execute_native_tool(name: str, args: dict) -> Any:
    """Dispatch a native tool call by name.

    Args:
        name: Tool name
        args: Tool arguments dict

    Returns:
        Tool result dict
    """
    handler = _native_handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown native tool: {name}")
    return await handler(**args)
