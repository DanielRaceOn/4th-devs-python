# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module configuration for image editing agent — API settings, dual image backend
(Gemini native vs OpenRouter), model selection, system prompt, and folder constants.

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

# Prefer OpenRouter if available; fall back to native Gemini
IMAGE_BACKEND: str = "openrouter" if _has_openrouter else "gemini"

API_CONFIG: dict = {
    "model": resolve_model_for_provider("gpt-5.2"),
    "vision_model": resolve_model_for_provider("gpt-5.2"),
    "max_output_tokens": 16384,
    "instructions": """You are an image editing assistant.

<style_guide>
Read workspace/style-guide.md before your first image action.
Use it to shape the prompt, composition, and finish quality.
</style_guide>

<workflow>
1. If the task is about editing or restyling an existing source image, first determine the exact filename in workspace/input.
2. If the filename is missing, ambiguous, or there are multiple matches, ask a short clarification question before generating.
3. For edit requests, use the exact workspace-relative path: workspace/input/<exact_filename>.
4. Generate or edit the image.
5. Run analyze_image on the result.
6. If the analyze_image verdict is retry, make a focused retry based on the blocking issues and prompt hint.
7. Stop when the verdict is accept, or after two targeted retries.
</workflow>

<quality_bar>
Aim for a result that satisfies the user's request and the main style-guide constraints.
Acceptable output is allowed when only small polish notes remain.
Retry only for blocking problems such as the wrong subject, broken layout, strong artifacts, unreadable required text, or clear style-guide violations.
</quality_bar>

<filename_rule>
Never guess, shorten, or wildcard filenames for edit requests.
Use the exact filename, for example workspace/input/SCR-20260131-ugqp.jpeg.
</filename_rule>

<communication>
Keep the tone calm and practical.
Ask for human input only when the request is ambiguous, the filename cannot be identified confidently, a new creative direction is needed, or repeated retries do not improve the same blocking issue.
</communication>""",
}

GEMINI_CONFIG: dict = {
    "api_key": GEMINI_API_KEY,
    "image_backend": IMAGE_BACKEND,
    "image_model": (
        "google/gemini-3.1-flash-image-preview"
        if IMAGE_BACKEND == "openrouter"
        else "gemini-3.1-flash-image-preview"
    ),
    "endpoint": "https://generativelanguage.googleapis.com/v1beta/interactions",
    "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
}

OUTPUT_FOLDER: str = "workspace/output"
