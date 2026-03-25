# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native video processing tools for the video agent. Defines the 4 tool schemas in
OpenAI Responses API function format and their async handler implementations:
- analyze_video   — visual/audio/action/general analysis
- transcribe_video — speech transcription with timestamps and speakers
- extract_video   — scenes / keyframes / objects / on-screen text extraction
- query_video     — free-form question about video content

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/native/tools.js`


"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any

from ..helpers.logger import log
from .gemini import (
    analyze_video,
    extract_from_video,
    process_video,
    transcribe_video,
    upload_video_file,
)

logger = logging.getLogger(__name__)

# Module root is 01_04_video/ (two dirs up from src/native/)
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent

# 20 MB threshold — files above this are uploaded via Gemini Files API
INLINE_SIZE_LIMIT: int = 20 * 1024 * 1024

# MIME types for supported video formats
_MIME_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpg",
    ".mov": "video/mov",
    ".avi": "video/avi",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".wmv": "video/wmv",
    ".3gp": "video/3gpp",
    ".3gpp": "video/3gpp",
}


def _get_video_mime_type(file_path: str) -> str:
    """Resolve MIME type from file extension.

    Args:
        file_path: Path string with an extension.

    Returns:
        MIME type string; falls back to ``"video/mp4"`` for unknown extensions.
    """
    ext = Path(file_path).suffix.lower()
    return _MIME_TYPES.get(ext, "video/mp4")


def _is_youtube_url(input_str: str) -> bool:
    """Return True when the input looks like a YouTube URL."""
    return "youtube.com/watch" in input_str or "youtu.be/" in input_str


def _build_video_metadata(
    start_time: str | None,
    end_time: str | None,
    fps: float | None = None,
) -> dict[str, Any] | None:
    """Build Gemini video_metadata dict for clipping / FPS settings.

    Args:
        start_time: Clip start offset string (e.g. ``"30s"``), or ``None``.
        end_time: Clip end offset string, or ``None``.
        fps: Frames per second to sample, or ``None``.

    Returns:
        Metadata dict when at least one field is set, otherwise ``None``.
    """
    metadata: dict[str, Any] = {}
    if start_time:
        metadata["start_offset"] = start_time
    if end_time:
        metadata["end_offset"] = end_time
    if fps is not None:
        metadata["fps"] = fps
    return metadata if metadata else None


async def _load_video(video_path: str) -> dict[str, Any]:
    """Load video and prepare it for Gemini.

    - YouTube URLs → returned as ``file_uri`` directly (no I/O).
    - Local files <= 20 MB → base64-encoded inline.
    - Local files > 20 MB → uploaded via Gemini Files API.

    Args:
        video_path: YouTube URL or path relative to ``PROJECT_ROOT``.

    Returns:
        Dict containing either ``file_uri`` + ``mime_type``, or
        ``video_base64`` + ``mime_type``.
    """
    if _is_youtube_url(video_path):
        log.info("YouTube URL detected")
        return {"file_uri": video_path, "mime_type": "video/mp4"}

    full_path = PROJECT_ROOT / video_path
    if not full_path.exists():
        # Use a path relative to PROJECT_ROOT in the message — avoid leaking
        # absolute filesystem paths to the LLM in error responses.
        raise FileNotFoundError(f"Video file not found: {video_path}")
    video_bytes = full_path.read_bytes()
    mime_type = _get_video_mime_type(video_path)
    display_name = Path(video_path).name

    if len(video_bytes) > INLINE_SIZE_LIMIT:
        log.info("Video file > 20 MB, using upload API...")
        uploaded = await upload_video_file(video_bytes, mime_type, display_name)
        return {"file_uri": uploaded["file_uri"], "mime_type": mime_type}
    else:
        # Small file — encode inline to avoid the upload round-trip
        return {
            "video_base64": base64.b64encode(video_bytes).decode(),
            "mime_type": mime_type,
        }


def _save_output(result: Any, output_name: str) -> str:
    """Save a result dict as JSON to ``workspace/output/`` and return the relative path.

    Args:
        result: Serialisable result dict to write.
        output_name: Base name for the output file (without timestamp or extension).

    Returns:
        Relative path string ``"workspace/output/{output_name}_{ts}.json"``.
    """
    output_dir = PROJECT_ROOT / "workspace" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    rel_path = f"workspace/output/{output_name}_{ts}.json"
    (PROJECT_ROOT / rel_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.success(f"Saved: {rel_path}")
    return rel_path


# ── Tool schema definitions (OpenAI Responses API function format) ───────────

native_tools: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "analyze_video",
        "description": (
            "Analyze video content - visual elements, audio, actions, and overall "
            "composition. Supports local files and YouTube URLs. Returns structured "
            "analysis with timestamps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": (
                        "Path to video file relative to project root "
                        "(e.g., workspace/input/video.mp4) OR a YouTube URL"
                    ),
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["general", "visual", "audio", "action"],
                    "description": (
                        "Type of analysis: 'general' (comprehensive), 'visual' "
                        "(cinematography, scenes), 'audio' (speech, music, sounds), "
                        "'action' (events, movements). Default: general"
                    ),
                },
                "custom_prompt": {
                    "type": "string",
                    "description": "Optional custom analysis prompt to override the default",
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start time for clipping (e.g., '30s' or '1m30s')",
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end time for clipping",
                },
                "fps": {
                    "type": "number",
                    "description": (
                        "Frames per second to sample (default: 1). "
                        "Lower for long videos, higher for fast action."
                    ),
                },
                "output_name": {
                    "type": "string",
                    "description": (
                        "Optional base name for saving analysis JSON to workspace/output/"
                    ),
                },
            },
            "required": ["video_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "transcribe_video",
        "description": (
            "Transcribe speech from video with timestamps and speaker detection. "
            "Also captures non-speech audio. Supports local files and YouTube URLs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": (
                        "Path to video file relative to project root OR a YouTube URL"
                    ),
                },
                "include_timestamps": {
                    "type": "boolean",
                    "description": "Include timestamps for each segment. Default: true",
                },
                "detect_speakers": {
                    "type": "boolean",
                    "description": "Identify and label different speakers. Default: true",
                },
                "translate_to": {
                    "type": "string",
                    "description": (
                        "Target language for translation (e.g., 'English', 'Spanish'). "
                        "If not provided, keeps original language."
                    ),
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start time for clipping (e.g., '30s' or '1m30s')",
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end time for clipping",
                },
                "output_name": {
                    "type": "string",
                    "description": (
                        "Optional base name for saving transcription JSON to workspace/output/"
                    ),
                },
            },
            "required": ["video_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "extract_video",
        "description": (
            "Extract specific elements from video: scenes, keyframes, objects, or text. "
            "Returns structured data with timestamps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": (
                        "Path to video file relative to project root OR a YouTube URL"
                    ),
                },
                "extraction_type": {
                    "type": "string",
                    "enum": ["scenes", "keyframes", "objects", "text"],
                    "description": (
                        "What to extract: 'scenes' (distinct scenes with timestamps), "
                        "'keyframes' (representative moments), 'objects' (people/things), "
                        "'text' (on-screen text). Default: scenes"
                    ),
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start time for clipping",
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end time for clipping",
                },
                "fps": {
                    "type": "number",
                    "description": (
                        "Frames per second to sample. Higher = more detail but more tokens."
                    ),
                },
                "output_name": {
                    "type": "string",
                    "description": (
                        "Optional base name for saving extraction JSON to workspace/output/"
                    ),
                },
            },
            "required": ["video_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "query_video",
        "description": (
            "Ask any question about a video. Use for custom queries that don't fit "
            "analyze/transcribe/extract patterns. Can reference specific timestamps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": (
                        "Path to video file relative to project root OR a YouTube URL"
                    ),
                },
                "question": {
                    "type": "string",
                    "description": (
                        "Question or prompt about the video content. "
                        "Can reference timestamps like 'What happens at 01:30?'"
                    ),
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start time to focus on specific segment",
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end time to focus on specific segment",
                },
            },
            "required": ["video_path", "question"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────────


async def _handle_analyze_video(args: dict[str, Any]) -> dict[str, Any]:
    """Handle the ``analyze_video`` tool call.

    Args:
        args: Tool arguments dict. Required key: ``video_path``. Optional keys:
            ``analysis_type`` (default ``"general"``), ``custom_prompt``,
            ``start_time``, ``end_time``, ``fps``, ``output_name``.

    Returns:
        On success: ``{"success": True, "video_path", "analysis_type", "analysis",
        "output_path"}`` (``output_path`` only when ``output_name`` is provided).
        On failure: ``{"success": False, "error": "<message>"}``.
    """
    video_path: str = args["video_path"]
    analysis_type: str = args.get("analysis_type", "general")
    custom_prompt: str | None = args.get("custom_prompt")
    start_time: str | None = args.get("start_time")
    end_time: str | None = args.get("end_time")
    fps: float | None = args.get("fps")
    output_name: str | None = args.get("output_name")

    try:
        video = await _load_video(video_path)
        video_metadata = _build_video_metadata(start_time, end_time, fps)

        result = await analyze_video(
            **video,
            analysis_type=analysis_type,
            custom_prompt=custom_prompt,
            video_metadata=video_metadata,
        )

        out: dict[str, Any] = {
            "success": True,
            "video_path": video_path,
            "analysis_type": analysis_type,
            "analysis": result,
        }
        if output_name:
            out["output_path"] = _save_output(result, output_name)
        else:
            log.success(f"Analyzed: {result.get('video_type', '?')}")
        return out

    except Exception as exc:
        log.error("analyze_video", str(exc))
        return {"success": False, "error": str(exc)}


async def _handle_transcribe_video(args: dict[str, Any]) -> dict[str, Any]:
    """Handle the ``transcribe_video`` tool call.

    Args:
        args: Tool arguments dict. Required key: ``video_path``. Optional keys:
            ``include_timestamps`` (default ``True``), ``detect_speakers`` (default
            ``True``), ``translate_to``, ``start_time``, ``end_time``, ``output_name``.

    Returns:
        On success: ``{"success": True, "video_path", "transcription",
        "output_path"}`` (``output_path`` only when ``output_name`` is provided).
        On failure: ``{"success": False, "error": "<message>"}``.
    """
    video_path: str = args["video_path"]
    include_timestamps: bool = args.get("include_timestamps", True)
    detect_speakers: bool = args.get("detect_speakers", True)
    translate_to: str | None = args.get("translate_to")
    start_time: str | None = args.get("start_time")
    end_time: str | None = args.get("end_time")
    output_name: str | None = args.get("output_name")

    try:
        video = await _load_video(video_path)
        video_metadata = _build_video_metadata(start_time, end_time)

        result = await transcribe_video(
            **video,
            include_timestamps=include_timestamps,
            detect_speakers=detect_speakers,
            target_language=translate_to,
            video_metadata=video_metadata,
        )

        out: dict[str, Any] = {"success": True, "video_path": video_path, "transcription": result}
        if output_name:
            out["output_path"] = _save_output(result, output_name)
        else:
            segments = result.get("segments") or []
            log.success(f"Transcribed: {len(segments)} segments")
        return out

    except Exception as exc:
        log.error("transcribe_video", str(exc))
        return {"success": False, "error": str(exc)}


async def _handle_extract_video(args: dict[str, Any]) -> dict[str, Any]:
    """Handle the ``extract_video`` tool call.

    Args:
        args: Tool arguments dict. Required key: ``video_path``. Optional keys:
            ``extraction_type`` (default ``"scenes"``), ``start_time``,
            ``end_time``, ``fps``, ``output_name``.

    Returns:
        On success: ``{"success": True, "video_path", "extraction_type",
        "extraction", "output_path"}`` (``output_path`` only when ``output_name``
        is provided).
        On failure: ``{"success": False, "error": "<message>"}``.
    """
    video_path: str = args["video_path"]
    extraction_type: str = args.get("extraction_type", "scenes")
    start_time: str | None = args.get("start_time")
    end_time: str | None = args.get("end_time")
    fps: float | None = args.get("fps")
    output_name: str | None = args.get("output_name")

    try:
        video = await _load_video(video_path)
        video_metadata = _build_video_metadata(start_time, end_time, fps)

        result = await extract_from_video(
            **video,
            extraction_type=extraction_type,
            video_metadata=video_metadata,
        )

        out: dict[str, Any] = {
            "success": True,
            "video_path": video_path,
            "extraction_type": extraction_type,
            "extraction": result,
        }
        if output_name:
            out["output_path"] = _save_output(result, output_name)
        else:
            log.success(f"Extracted {extraction_type}")
        return out

    except Exception as exc:
        log.error("extract_video", str(exc))
        return {"success": False, "error": str(exc)}


async def _handle_query_video(args: dict[str, Any]) -> dict[str, Any]:
    """Handle the ``query_video`` tool call.

    Args:
        args: Tool arguments dict. Required keys: ``video_path``, ``question``.
            Optional keys: ``start_time``, ``end_time``.

    Returns:
        On success: ``{"success": True, "video_path", "question", "answer"}``.
        On failure: ``{"success": False, "error": "<message>"}``.
    """
    video_path: str = args["video_path"]
    question: str = args["question"]
    start_time: str | None = args.get("start_time")
    end_time: str | None = args.get("end_time")

    log.tool(
        "query_video",
        {"video_path": video_path[:50], "question": question[:50] + ("..." if len(question) > 50 else "")},
    )

    try:
        video = await _load_video(video_path)
        video_metadata = _build_video_metadata(start_time, end_time)

        result = await process_video(**video, prompt=question, video_metadata=video_metadata)

        log.success(f"Query answered ({len(str(result))} chars)")
        return {
            "success": True,
            "video_path": video_path,
            "question": question,
            "answer": result,
        }

    except Exception as exc:
        log.error("query_video", str(exc))
        return {"success": False, "error": str(exc)}


# Handler registry — maps tool name to handler function
_HANDLERS: dict[str, Any] = {
    "analyze_video": _handle_analyze_video,
    "transcribe_video": _handle_transcribe_video,
    "extract_video": _handle_extract_video,
    "query_video": _handle_query_video,
}


def is_native_tool(name: str) -> bool:
    """Return True when ``name`` is a registered native tool.

    Args:
        name: Tool name to check.

    Returns:
        ``True`` if handled natively, ``False`` if it should go to MCP.
    """
    return name in _HANDLERS


async def execute_native_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a native tool call by name.

    Args:
        name: Tool name (must be in ``_HANDLERS``).
        args: Parsed argument dict from the LLM.

    Returns:
        Tool result dict.

    Raises:
        ValueError: When ``name`` is not a known native tool.
    """
    handler = _HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown native tool: {name}")
    return await handler(args)
