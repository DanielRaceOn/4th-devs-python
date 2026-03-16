# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions and handlers for the PDF reports agent.

Tools:
- create_image: Generate or edit images (reference_images optional)
- analyze_image: Evaluate image quality and return ACCEPT/RETRY verdict
- html_to_pdf: Convert an HTML file to PDF via Playwright (Python equivalent of Puppeteer)

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/tools.js

"""

import base64
import re
import time
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
            "Generate or edit images using Gemini. If reference_images is empty, "
            "generates from prompt. If reference_images provided, edits/combines them "
            "based on the prompt."
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
                        "Optional paths to reference image(s) for editing. "
                        "Empty array = generate from scratch."
                    ),
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                    "description": "Aspect ratio of the output image. Default is 1:1",
                },
                "image_size": {
                    "type": "string",
                    "enum": ["1k", "2k", "4k"],
                    "description": "Resolution of the output image. Default is 1k",
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
            "Analyze a generated or edited image for quality issues. "
            "Checks for prompt adherence, visual artifacts, style consistency, "
            "and common AI generation mistakes."
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
    {
        "type": "function",
        "name": "html_to_pdf",
        "description": (
            "Convert an HTML file to PDF. The HTML file should already exist in workspace/html/. "
            "Images in the HTML must use absolute paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "html_path": {
                    "type": "string",
                    "description": (
                        "Path to the HTML file relative to project root "
                        "(e.g., workspace/html/report.html)"
                    ),
                },
                "output_name": {
                    "type": "string",
                    "description": (
                        "Base name for the output PDF file (without extension). "
                        "Will be saved to workspace/output/"
                    ),
                },
                "options": {
                    "type": "object",
                    "description": "PDF generation options",
                    "properties": {
                        "format": {
                            "type": "string",
                            "enum": ["A4", "Letter"],
                            "description": "Page format. Default: A4",
                        },
                        "landscape": {
                            "type": "boolean",
                            "description": "Use landscape orientation. Default: false",
                        },
                        "margin": {
                            "type": "object",
                            "description": "Page margins in CSS units (e.g., '20mm')",
                            "properties": {
                                "top": {"type": "string"},
                                "right": {"type": "string"},
                                "bottom": {"type": "string"},
                                "left": {"type": "string"},
                            },
                        },
                        "print_background": {
                            "type": "boolean",
                            "description": "Include CSS backgrounds. Default: true",
                        },
                    },
                },
            },
            "required": ["html_path", "output_name"],
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


async def _handle_html_to_pdf(
    html_path: str,
    output_name: str,
    options: Optional[dict] = None,
) -> dict:
    """Convert an HTML file to PDF using Playwright (Python equivalent of Puppeteer).

    Playwright's async API mirrors Puppeteer very closely: launch browser →
    new page → goto file:// URL → pdf() → close.  The ``print_background``
    option maps to Playwright's ``print_background`` PDF parameter, which is
    required for dark-themed templates to render correctly.

    Args:
        html_path: Workspace-relative path to the HTML source file.
        output_name: Base filename prefix for the PDF (no extension).
        options: Optional dict with keys: format, landscape, margin, print_background.

    Returns:
        Dict with success flag, output paths, and applied options.
    """
    log.tool("html_to_pdf", {"html_path": html_path, "output_name": output_name})

    try:
        # Import here so the module loads even if playwright is not installed;
        # the tool will only fail when actually called.
        from playwright.async_api import async_playwright  # type: ignore[import]
    except ImportError:
        return {
            "success": False,
            "error": (
                "playwright is not installed. "
                "Run: .venv/Scripts/python -m pip install playwright && "
                ".venv/Scripts/python -m playwright install chromium"
            ),
        }

    try:
        opts = options or {}
        full_html_path = _PROJECT_ROOT / html_path

        if not full_html_path.exists():
            return {"success": False, "error": f"HTML file not found: {html_path}"}

        output_dir = _PROJECT_ROOT / "workspace" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        output_filename = f"{output_name}_{timestamp}.pdf"
        output_path = output_dir / output_filename

        # Build Playwright PDF options (same semantics as Puppeteer)
        margin = opts.get("margin", {"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"})
        pdf_options: dict = {
            "path": str(output_path),
            "format": opts.get("format", "A4"),
            "landscape": opts.get("landscape", False),
            "print_background": opts.get("print_background", True),
            "margin": margin,
        }

        log.info("Launching browser for PDF conversion...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                # Use file:// URL so local assets (fonts, images) resolve correctly
                file_url = full_html_path.as_uri()
                await page.goto(file_url, wait_until="networkidle")
                await page.pdf(**pdf_options)
            finally:
                await browser.close()

        relative_path = f"workspace/output/{output_filename}"
        log.success(f"PDF created: {relative_path}")

        return {
            "success": True,
            "output_path": relative_path,
            "absolute_path": str(output_path),
            "project_root": str(_PROJECT_ROOT),
            "html_source": html_path,
            "options": pdf_options,
        }

    except Exception as error:
        log.error("html_to_pdf", str(error))
        return {"success": False, "error": str(error)}


_NATIVE_HANDLERS: dict = {
    "create_image": _handle_create_image,
    "analyze_image": _handle_analyze_image,
    "html_to_pdf": _handle_html_to_pdf,
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
