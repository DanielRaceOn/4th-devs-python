# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
HTTP client configuration and agent settings for the Video Processing agent module.
Handles provider selection (OpenAI / OpenRouter), API key resolution, Gemini config,
and model/system-prompt definitions.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/config.js`, `../../config.js`


"""

import logging
import os
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Two levels up: 01_04_video/src -> 01_04_video -> repo root
_ROOT_DIR = Path(__file__).parent.parent.parent
_ROOT_ENV_FILE = _ROOT_DIR / ".env"

if _ROOT_ENV_FILE.exists():
    load_dotenv(_ROOT_ENV_FILE)
    logger.debug("Loaded .env from %s", _ROOT_ENV_FILE)
else:
    logger.debug("No .env found at %s", _ROOT_ENV_FILE)

_OPENAI_API_KEY: str = (os.environ.get("OPENAI_API_KEY") or "").strip()
_OPENROUTER_API_KEY: str = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
_requested_provider: str = (os.environ.get("AI_PROVIDER") or "").strip().lower()

_has_openai: bool = bool(_OPENAI_API_KEY)
_has_openrouter: bool = bool(_OPENROUTER_API_KEY)

if not _has_openai and not _has_openrouter:
    raise RuntimeError(
        "API key is not set. Add OPENAI_API_KEY or OPENROUTER_API_KEY to .env"
    )

if _requested_provider and _requested_provider not in ("openai", "openrouter"):
    raise RuntimeError("AI_PROVIDER must be one of: openai, openrouter")

if _requested_provider == "openai" and not _has_openai:
    raise RuntimeError("AI_PROVIDER=openai requires OPENAI_API_KEY")
if _requested_provider == "openrouter" and not _has_openrouter:
    raise RuntimeError("AI_PROVIDER=openrouter requires OPENROUTER_API_KEY")

AI_PROVIDER: str = (
    _requested_provider
    if _requested_provider
    else ("openai" if _has_openai else "openrouter")
)

AI_API_KEY: str = _OPENAI_API_KEY if AI_PROVIDER == "openai" else _OPENROUTER_API_KEY

RESPONSES_API_ENDPOINT: str = (
    "https://api.openai.com/v1/responses"
    if AI_PROVIDER == "openai"
    else "https://openrouter.ai/api/v1/responses"
)

EXTRA_API_HEADERS: dict[str, str] = {}
if AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        EXTRA_API_HEADERS["X-Title"] = _app_name

# Validate Gemini API key — required for video processing
GEMINI_API_KEY: str = (os.environ.get("GEMINI_API_KEY") or "").strip()
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set.\n"
        "       Add it to the repo root .env file: GEMINI_API_KEY=..."
    )

logger.debug("AI_PROVIDER=%s, endpoint=%s", AI_PROVIDER, RESPONSES_API_ENDPOINT)


def resolve_model_for_provider(model: str) -> str:
    """Resolve model name for the configured provider.

    For OpenRouter, prepends ``openai/`` when the model string contains no slash.

    Args:
        model: Raw model identifier (e.g. ``gpt-4.1``).

    Returns:
        Provider-appropriate model string.
    """
    if not model or not model.strip():
        raise ValueError("Model must be a non-empty string")
    if AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"


# System prompt for the orchestrator agent (verbatim from JS config.js)
_INSTRUCTIONS = """You are an autonomous video processing agent.

## GOAL
Process, analyze, transcribe, and extract information from videos. Handle both local files and YouTube URLs.

## RESOURCES
- workspace/input/   → Source video files to process
- workspace/output/  → Generated analysis, transcriptions, extractions (JSON)

## TOOLS
- MCP file tools: read, write, list, search files
- analyze_video: Analyze video content (visual, audio, action, general)
- transcribe_video: Transcribe speech with timestamps and speaker detection
- extract_video: Extract scenes, keyframes, objects, or on-screen text
- query_video: Ask any custom question about video content

## VIDEO INPUT
Supported sources:
- Local files: workspace/input/video.mp4
- YouTube URLs: https://www.youtube.com/watch?v=... or https://youtu.be/...

Supported formats: MP4, MPEG, MOV, AVI, FLV, WebM, WMV, 3GP

## FEATURES

Analysis types:
- general: Comprehensive overview (visual + audio + content)
- visual: Cinematography, scenes, colors, composition
- audio: Speech, music, sound effects
- action: Events, movements, interactions

Extraction types:
- scenes: Distinct scenes with start/end timestamps
- keyframes: Representative moments
- objects: People, items, elements with visibility timestamps
- text: On-screen text, titles, captions

Video clipping:
- Use start_time/end_time to focus on specific segments
- Format: "30s", "1m30s", "90s"

FPS control:
- Default: 1 FPS (1 frame per second)
- Lower (<1) for long videos to reduce tokens
- Higher (>1) for fast action sequences

## WORKFLOW

1. UNDERSTAND THE REQUEST
   - What does the user need? Analysis? Transcription? Extraction?
   - Is it a local file or YouTube URL?
   - Any specific time range to focus on?

2. CHOOSE THE RIGHT TOOL
   - Want to understand the video? → analyze_video
   - Need speech as text? → transcribe_video
   - Looking for specific elements? → extract_video
   - Custom question? → query_video

3. PROCESS AND DELIVER
   - Use timestamps (MM:SS) when referencing moments
   - Save results to workspace/output/ when requested
   - Summarize long results

## RULES

1. Check workspace/input/ for local files
2. YouTube URLs work directly - no download needed
3. Large files (>20MB) are uploaded automatically
4. Use clipping for long videos to reduce processing time
5. Reference timestamps in MM:SS format
6. One video per request works best

## TOKENIZATION
- ~300 tokens/second at default resolution
- ~100 tokens/second at low resolution
- 1 hour video ≈ 1M tokens

Run autonomously. Report results with timestamps."""

# ``api`` namespace mirrors the JS ``api`` object exported from config.js.
# Accessed as ``api.model``, ``api.max_output_tokens``, ``api.instructions``.
api = SimpleNamespace(
    model=resolve_model_for_provider("gpt-4.1"),
    max_output_tokens=16384,
    instructions=_INSTRUCTIONS,
)

# ``gemini`` namespace mirrors the JS ``gemini`` object.
# Accessed as ``gemini.api_key``, ``gemini.video_model``.
gemini = SimpleNamespace(
    api_key=GEMINI_API_KEY,
    video_model="gemini-2.5-flash",
)

OUTPUT_FOLDER: str = "workspace/output"
