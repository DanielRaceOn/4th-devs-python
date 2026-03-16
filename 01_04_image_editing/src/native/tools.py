# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions and handlers for the image editing agent.

Tools:
- create_image: Generate or edit images (reference_images optional)
- analyze_image: Evaluate image quality and return ACCEPT/RETRY verdict

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/tools.js

"""

import base64
import re
from pathlib import Path
from typing import Optional

from .gemini import generate_image, edit_image, edit_image_with_references
from .vision import vision
from ..helpers.logger import log

# Module root: src/native/ → src/ → module root
_PROJECT_ROOT = Path(__file__).parent.parent.parent


# ── MIME / extension helpers ───────────────────────────────────────────────

_MIME_MAP: dict = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

_EXT_MAP: dict = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _get_mime_type(filepath: str) -> str:
    return _MIME_MAP.get(Path(filepath).suffix.lower(), "image/png")


def _get_extension(mime_type: str) -> str:
    return _EXT_MAP.get(mime_type, ".png")


def _generate_filename(prefix: str, mime_type: str) -> str:
    """Create a unique timestamped filename.

    Args:
        prefix: Base name prefix (output_name from the tool call).
        mime_type: MIME type to determine file extension.

    Returns:
        Filename string, e.g. ``"sketch_1710000000000.png"``.
    """
    import time
    timestamp = int(time.time() * 1000)
    ext = _get_extension(mime_type)
    return f"{prefix}_{timestamp}{ext}"


# ── Analysis report parsing ────────────────────────────────────────────────

def _extract_tagged_value(text: str, tag: str) -> str:
    match = re.search(rf"^{tag}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_bullet_section(text: str, section: str) -> list:
    """Extract bullet items from a named section in the analysis report.

    Args:
        text: Full analysis text.
        section: Section header name (e.g. ``"BLOCKING_ISSUES"``).

    Returns:
        List of bullet item strings.
    """
    lines = text.split("\n")
    header = f"{section}:"
    start_index = next(
        (i for i, line in enumerate(lines) if line.strip().upper() == header),
        -1,
    )

    if start_index == -1:
        return []

    items = []
    for line in lines[start_index + 1:]:
        trimmed = line.strip()
        if not trimmed:
            continue
        # Stop at the next section header (ALL_CAPS word(s) followed by colon)
        if re.match(r"^[A-Z_ ]+:$", trimmed):
            break
        if trimmed.startswith("- "):
            items.append(trimmed[2:].strip())

    return items


def _parse_analysis_report(analysis: str) -> dict:
    raw_verdict = _extract_tagged_value(analysis, "VERDICT").upper()
    score_text = _extract_tagged_value(analysis, "SCORE")

    try:
        score: Optional[int] = int(score_text)
    except (ValueError, TypeError):
        score = None

    return {
        "verdict": "retry" if raw_verdict == "RETRY" else "accept",
        "score": score,
        "blocking_issues": _extract_bullet_section(analysis, "BLOCKING_ISSUES"),
        "minor_issues": _extract_bullet_section(analysis, "MINOR_ISSUES"),
        "next_prompt_hints": _extract_bullet_section(analysis, "NEXT_PROMPT_HINT"),
    }


# ── Native tool definitions (OpenAI function format) ──────────────────────

native_tools: list = [
    {
        "type": "function",
        "name": "create_image",
        "description": (
            "Generate or edit images. For edits, reference_images must use exact "
            "workspace-relative filenames such as workspace/input/SCR-20260131-ugqp.jpeg. "
            "Never use wildcards or guessed paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Description of image to generate, or instructions for editing "
                        "reference images. Be specific about style, composition, colors, changes."
                    ),
                },
                "output_name": {
                    "type": "string",
                    "description": (
                        "Base name for the output file (without extension). "
                        "Will be saved to workspace/output/"
                    ),
                },
                "reference_images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional exact workspace-relative paths to reference image(s) for "
                        "editing, for example workspace/input/SCR-20260131-ugqp.jpeg. "
                        "Empty array = generate from scratch."
                    ),
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                    "description": (
                        "Optional aspect ratio for the output image. "
                        "If omitted, follow the style guide or user request."
                    ),
                },
                "image_size": {
                    "type": "string",
                    "enum": ["1k", "2k", "4k"],
                    "description": (
                        "Optional image size. If omitted, follow the style guide or user request."
                    ),
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
            "Analyze a generated or edited image and return an ACCEPT or RETRY verdict. "
            "RETRY should be used only for blocking issues, while minor polish notes "
            "should still allow ACCEPT."
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
                    "description": "The original prompt or instructions used to generate/edit the image",
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
                    "description": (
                        "Specific aspects to check. If not provided, checks all aspects."
                    ),
                },
            },
            "required": ["image_path", "original_prompt"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]


# ── Native tool handlers ───────────────────────────────────────────────────

async def _handle_create_image(
    prompt: str,
    output_name: str,
    reference_images: list,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> dict:
    """Generate or edit an image and save it to workspace/output/.

    Args:
        prompt: Generation prompt or editing instructions.
        output_name: Base filename prefix (no extension).
        reference_images: Workspace-relative paths to source images for editing.
        aspect_ratio: Optional aspect ratio string.
        image_size: Optional image size string.

    Returns:
        Dict describing the result (success, mode, output_path, etc.).
    """
    is_editing = bool(reference_images)
    mode = "edit" if is_editing else "generate"

    try:
        options: dict = {}
        if aspect_ratio:
            options["aspectRatio"] = aspect_ratio
        if image_size:
            options["imageSize"] = image_size

        if is_editing:
            loaded_images = []
            for img_path in reference_images:
                full_path = _PROJECT_ROOT / img_path
                image_bytes = full_path.read_bytes()
                image_base64 = base64.b64encode(image_bytes).decode()
                mime_type = _get_mime_type(img_path)
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

        # Save image to workspace/output/
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
            "mime_type": result["mimeType"],
            "prompt_used": prompt,
            "reference_images": reference_images or [],
        }

    except Exception as error:
        log.error("create_image", str(error))
        return {"success": False, "error": str(error)}


async def _handle_analyze_image(
    image_path: str,
    original_prompt: str,
    check_aspects: Optional[list] = None,
) -> dict:
    """Analyse an image for quality issues and return a structured report.

    Args:
        image_path: Workspace-relative path to the image to analyse.
        original_prompt: The prompt that produced the image.
        check_aspects: List of aspect names to evaluate (defaults to all six).

    Returns:
        Dict with verdict, score, issues, hints, and the raw analysis text.
    """
    try:
        full_path = _PROJECT_ROOT / image_path
        image_bytes = full_path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode()
        mime_type = _get_mime_type(image_path)

        aspects = check_aspects or [
            "prompt_adherence",
            "visual_artifacts",
            "anatomy",
            "text_rendering",
            "style_consistency",
            "composition",
        ]

        aspect_lines = []
        if "prompt_adherence" in aspects:
            aspect_lines.append(
                "1. PROMPT ADHERENCE: Does the image accurately represent what was requested? "
                "What elements match or are missing?"
            )
        if "visual_artifacts" in aspects:
            aspect_lines.append(
                "2. VISUAL ARTIFACTS: Are there any glitches, distortions, blur, noise, "
                "or unnatural patterns?"
            )
        if "anatomy" in aspects:
            aspect_lines.append(
                "3. ANATOMY: If there are people/animals, check for correct proportions, "
                "especially hands, fingers, faces, and limbs."
            )
        if "text_rendering" in aspects:
            aspect_lines.append(
                "4. TEXT RENDERING: If text was requested, is it readable and correctly spelled?"
            )
        if "style_consistency" in aspects:
            aspect_lines.append(
                "5. STYLE CONSISTENCY: Is the visual style coherent throughout the image?"
            )
        if "composition" in aspects:
            aspect_lines.append(
                "6. COMPOSITION: Is the framing and layout balanced and appropriate?"
            )

        analysis_prompt = (
            f'Analyze this AI-generated image for quality issues. The original prompt was:\n'
            f'"{original_prompt}"\n\n'
            f"Please evaluate the following aspects:\n\n"
            + "\n".join(aspect_lines)
            + """

Use this exact output format:

VERDICT: ACCEPT or RETRY
SCORE: <1-10>
BLOCKING_ISSUES:
- <only issues that materially break the brief; use "none" if there are none>
MINOR_ISSUES:
- <optional polish notes that do not require another retry; use "none" if there are none>
NEXT_PROMPT_HINT:
- <targeted retry hint only if VERDICT is RETRY; otherwise use "none">

Decision rules:
- Use ACCEPT when the main subject, layout intent, and style-guide essentials are satisfied, even if minor polish notes remain.
- Use RETRY only when there are blocking issues such as wrong subject, broken composition, unreadable required text, severe artifacts, or clear style-guide violations.
- Do NOT use RETRY for small polish improvements alone."""
        )

        log.vision(image_path, "Quality analysis")

        analysis = await vision(
            image_base64=image_base64,
            mime_type=mime_type,
            question=analysis_prompt,
        )

        log.vision_result(analysis[:150] + "...")

        report = _parse_analysis_report(analysis)

        return {
            "success": True,
            "image_path": image_path,
            "original_prompt": original_prompt,
            "aspects_checked": aspects,
            "verdict": report["verdict"],
            "score": report["score"],
            "blocking_issues": report["blocking_issues"],
            "minor_issues": report["minor_issues"],
            "next_prompt_hints": report["next_prompt_hints"],
            "analysis": analysis,
        }

    except Exception as error:
        log.error("analyze_image", str(error))
        return {"success": False, "error": str(error)}


_NATIVE_HANDLERS: dict = {
    "create_image": _handle_create_image,
    "analyze_image": _handle_analyze_image,
}


def is_native_tool(name: str) -> bool:
    """Return ``True`` if ``name`` is a native (non-MCP) tool.

    Args:
        name: Tool name to check.
    """
    return name in _NATIVE_HANDLERS


async def execute_native_tool(name: str, args: dict) -> dict:
    """Dispatch a native tool call by name.

    Args:
        name: Tool name to invoke.
        args: Arguments dict for the tool.

    Returns:
        Tool result dict.

    Raises:
        Exception: If ``name`` is not a known native tool.
    """
    handler = _NATIVE_HANDLERS.get(name)
    if not handler:
        raise Exception(f"Unknown native tool: {name}")
    return await handler(**args)
