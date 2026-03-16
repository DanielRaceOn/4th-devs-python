# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module configuration for video generation agent — API settings, dual image backend
(Gemini native vs OpenRouter), Replicate/Kling video generation, model selection, and system prompt.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/config.js

"""

import os
import sys
from pathlib import Path

# Repo root is 2 levels above this file: src/ → module root → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from config import (  # type: ignore[import]
        resolve_model_for_provider,
        AI_API_KEY,
        EXTRA_API_HEADERS,
        RESPONSES_API_ENDPOINT,
        OPENROUTER_API_KEY,
    )
except ImportError:
    AI_API_KEY: str = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY") or ""
    EXTRA_API_HEADERS: dict = {}
    RESPONSES_API_ENDPOINT: str = "https://api.openai.com/v1/responses"

    def resolve_model_for_provider(model: str) -> str:  # type: ignore[misc]
        """Fallback: return model name unchanged."""
        return model


GEMINI_API_KEY: str = (os.getenv("GEMINI_API_KEY") or "").strip()

_has_gemini = bool(GEMINI_API_KEY)
_has_openrouter = bool(OPENROUTER_API_KEY)

if not _has_gemini and not _has_openrouter:
    print("\033[31mError: image generation backend is not configured\033[0m", file=sys.stderr)
    print("       Add one of these to the repo root .env file:", file=sys.stderr)
    print("       OPENROUTER_API_KEY=sk-or-v1-...   # uses google/gemini-3.1-flash-image-preview", file=sys.stderr)
    print("       GEMINI_API_KEY=...                # uses native Gemini image generation", file=sys.stderr)
    sys.exit(1)

if not os.getenv("REPLICATE_API_TOKEN"):
    print("\033[31mError: REPLICATE_API_TOKEN environment variable is not set\033[0m", file=sys.stderr)
    print("       Add it to the repo root .env file: REPLICATE_API_TOKEN=...", file=sys.stderr)
    sys.exit(1)

# Prefer OpenRouter if available; fall back to native Gemini
IMAGE_BACKEND: str = "openrouter" if _has_openrouter else "gemini"

API_CONFIG: dict = {
    "model": resolve_model_for_provider("gpt-4.1"),
    "vision_model": resolve_model_for_provider("gpt-4.1"),
    "max_output_tokens": 16384,
    "instructions": """You are a video generation agent using JSON-based prompting for consistent frame generation.

## WORKFLOW

### Step 1: Generate START Frame
1. Copy workspace/template.json → workspace/prompts/{scene}_{timestamp}.json
2. Edit ONLY the "subject" section for the STARTING pose/state
3. Read complete JSON, pass to create_image (aspect_ratio: "16:9", image_size: "2k")
4. Output: {scene}_frame_start_{timestamp}.png

### Step 2: Generate END Frame (from start frame)
1. Use create_image with reference_images: [start_frame_path]
2. Prompt describes the END state while referencing the start frame for character consistency
3. Example: "Same fox character, now landed in the snowdrift, snow particles around, happy expression"
4. Output: {scene}_frame_end_{timestamp}.png

### Step 3: Generate Video
Use image_to_video with BOTH frames:
- start_image: path to start frame
- end_image: path to end frame
- prompt: describes the motion between frames

## WHEN TO SKIP END FRAME REFERENCE
Only generate end frame WITHOUT referencing start frame if:
- Character transforms completely (caterpillar → butterfly)
- Scene changes entirely (day → night with different location)
- User explicitly asks for dramatic change

Otherwise, ALWAYS use start frame as reference for end frame to maintain character consistency.

## Subject Section Format
{
  "subject": {
    "main": "happy red fox preparing to jump",
    "details": "fluffy orange fur, white chest, alert ears, bushy tail raised",
    "orientation": "side view facing right, legs bent ready to spring",
    "position": "left third of frame",
    "scale": "occupies 40% of frame height"
  }
}

## END FRAME Editing Prompt Example
When editing start frame to create end frame:
"Same fox character with identical fur colors and markings, now landed in a fluffy snowdrift. Fox is partially buried in snow up to chest, snow particles floating around, joyful expression with eyes closed, tail visible above snow. Keep exact same art style and line quality."

## Video Motion Prompt
Describe the transition between start and end frames:
"The fox leaps gracefully from the fence, arcs through the air with tail flowing, and lands softly in the snowdrift sending snow particles flying"

## RULES
- **START + END**: Always generate both frames for better video control
- **END FROM START**: Use start frame as reference when creating end frame (character consistency)
- **COPY FIRST**: Create new prompt file, never edit template.json directly
- **MINIMAL EDITS**: Only edit "subject" section, preserve style/colors/composition
- **16:9 FOR VIDEO**: Always use 16:9 aspect ratio

## FILE NAMING
- Start frame: {scene}_frame_start_{timestamp}.png
- End frame: {scene}_frame_end_{timestamp}.png
- Video: {scene}_video_{timestamp}.mp4

## DEFAULTS
- Duration: 10 seconds
- Aspect ratio: 16:9
- Resolution: 2k

Run autonomously. Report all output paths when complete.""",
}

GEMINI_CONFIG: dict = {
    "api_key": GEMINI_API_KEY,
    "image_backend": IMAGE_BACKEND,
    "image_model": (
        "google/gemini-3.1-flash-image-preview"
        if IMAGE_BACKEND == "openrouter"
        else "gemini-3-pro-image-preview"
    ),
    "video_model": "gemini-2.5-flash",
    "endpoint": "https://generativelanguage.googleapis.com/v1beta/interactions",
    "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
}

OUTPUT_FOLDER: str = "workspace/output"
