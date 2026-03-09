# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Root configuration for AI provider selection, API key resolution, and endpoint setup.
Mirrors the root config.js — loads .env, validates keys, and exposes shared constants
and helpers consumed by all lesson modules.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `config.js`

"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
ROOT_ENV_FILE = ROOT_DIR / ".env"

RESPONSES_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "openrouter": "https://openrouter.ai/api/v1/responses",
}
VALID_PROVIDERS = {"openai", "openrouter"}

if ROOT_ENV_FILE.exists():
    load_dotenv(ROOT_ENV_FILE)

OPENAI_API_KEY: str = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENROUTER_API_KEY: str = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
_requested_provider: str = (os.environ.get("AI_PROVIDER") or "").strip().lower()

_has_openai_key = bool(OPENAI_API_KEY)
_has_openrouter_key = bool(OPENROUTER_API_KEY)

if not _has_openai_key and not _has_openrouter_key:
    print("\033[31mError: API key is not set\033[0m", file=sys.stderr)
    print(f"       Create: {ROOT_ENV_FILE}", file=sys.stderr)
    print("       Add one of:", file=sys.stderr)
    print("       OPENAI_API_KEY=sk-...", file=sys.stderr)
    print("       OPENROUTER_API_KEY=sk-or-v1-...", file=sys.stderr)
    sys.exit(1)

if _requested_provider and _requested_provider not in VALID_PROVIDERS:
    print(
        "\033[31mError: AI_PROVIDER must be one of: openai, openrouter\033[0m",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_provider() -> str:
    if _requested_provider:
        if _requested_provider == "openai" and not _has_openai_key:
            print(
                "\033[31mError: AI_PROVIDER=openai requires OPENAI_API_KEY\033[0m",
                file=sys.stderr,
            )
            sys.exit(1)
        if _requested_provider == "openrouter" and not _has_openrouter_key:
            print(
                "\033[31mError: AI_PROVIDER=openrouter requires OPENROUTER_API_KEY\033[0m",
                file=sys.stderr,
            )
            sys.exit(1)
        return _requested_provider
    return "openai" if _has_openai_key else "openrouter"


AI_PROVIDER: str = _resolve_provider()
AI_API_KEY: str = OPENAI_API_KEY if AI_PROVIDER == "openai" else OPENROUTER_API_KEY
RESPONSES_API_ENDPOINT: str = RESPONSES_ENDPOINTS[AI_PROVIDER]

EXTRA_API_HEADERS: dict = {}
if AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        EXTRA_API_HEADERS["X-Title"] = _app_name


def resolve_model_for_provider(model: str) -> str:
    """Return the model identifier adjusted for the active provider.

    Args:
        model: Base model name, e.g. ``'gpt-5.2'``.

    Returns:
        Model string ready to send to the API.

    Raises:
        ValueError: If ``model`` is not a non-empty string.
    """
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must be a non-empty string")

    if AI_PROVIDER != "openrouter" or "/" in model:
        return model

    return f"openai/{model}" if model.startswith("gpt-") else model
