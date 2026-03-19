# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
HTTP client configuration — provider selection, API key resolution, model
prefix logic, and request headers for the Daily Ops agent module.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      src/config.ts, ../../config.js


"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root (two levels up: 02_04_ops/src -> 02_04_ops -> project root)
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

_has_openai_key: bool = bool(_OPENAI_API_KEY)
_has_openrouter_key: bool = bool(_OPENROUTER_API_KEY)

if not _has_openai_key and not _has_openrouter_key:
    raise RuntimeError(
        "API key is not set. Add OPENAI_API_KEY or OPENROUTER_API_KEY to .env"
    )

if _requested_provider and _requested_provider not in ("openai", "openrouter"):
    raise RuntimeError("AI_PROVIDER must be one of: openai, openrouter")

if _requested_provider == "openai" and not _has_openai_key:
    raise RuntimeError("AI_PROVIDER=openai requires OPENAI_API_KEY")
if _requested_provider == "openrouter" and not _has_openrouter_key:
    raise RuntimeError("AI_PROVIDER=openrouter requires OPENROUTER_API_KEY")

AI_PROVIDER: str = (
    _requested_provider
    if _requested_provider
    else ("openai" if _has_openai_key else "openrouter")
)

AI_API_KEY: str = _OPENAI_API_KEY if AI_PROVIDER == "openai" else _OPENROUTER_API_KEY

CHAT_COMPLETIONS_ENDPOINT: str = (
    "https://api.openai.com/v1/chat/completions"
    if AI_PROVIDER == "openai"
    else "https://openrouter.ai/api/v1/chat/completions"
)

EXTRA_API_HEADERS: dict[str, str] = {}
if AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        EXTRA_API_HEADERS["X-Title"] = _app_name

logger.debug("AI_PROVIDER=%s, endpoint=%s", AI_PROVIDER, CHAT_COMPLETIONS_ENDPOINT)


def resolve_model_for_provider(model: str) -> str:
    """Resolve model name for the configured provider.

    For OpenRouter, prepends ``openai/`` when the model string contains no
    slash, mirroring the JS ``resolveModelForProvider`` logic.

    Args:
        model: Raw model identifier (e.g. ``gpt-4.1-mini``).

    Returns:
        Provider-appropriate model string.
    """
    if not model or not model.strip():
        raise ValueError("Model must be a non-empty string")
    if AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"
