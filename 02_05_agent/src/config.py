# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Configuration constants, API endpoint resolver, and model helper for the
02_05_agent context-engineering agent module.

Uses raw httpx (no OpenAI SDK). Targets the OpenAI Responses API
(/v1/responses), which is required for the structured tool-use format
used by the agent and memory subsystems.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/config.ts, ../../config.js


"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Module root: 02_05_agent/
MODULE_DIR = Path(__file__).parent.parent

# Workspace directory sandboxed to 02_05_agent/workspace/
WORKSPACE = MODULE_DIR / "workspace"

# Memory log output directory
MEMORY_DIR = WORKSPACE / "memory"

# Load .env from project root (three levels up: src -> 02_05_agent -> root)
_ROOT_DIR = MODULE_DIR.parent
_ROOT_ENV_FILE = _ROOT_DIR / ".env"

if _ROOT_ENV_FILE.exists():
    load_dotenv(_ROOT_ENV_FILE)
    logger.debug("Loaded .env from %s", _ROOT_ENV_FILE)
else:
    logger.debug("No .env found at %s", _ROOT_ENV_FILE)

# ---------------------------------------------------------------------------
# Provider / key resolution  (mirrors config.js + 02_04_ops/src/config.py)
# ---------------------------------------------------------------------------

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

# Responses API endpoint (distinct from chat/completions used in other modules)
RESPONSES_ENDPOINT: str = (
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

logger.debug("AI_PROVIDER=%s, endpoint=%s", AI_PROVIDER, RESPONSES_ENDPOINT)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

SERVER_PORT: int = 3001

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

DEFAULT_AGENT_NAME: str = "alice"
AGENT_MAX_TURNS: int = 25

# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

# Rough chars-per-token ratio used for initial estimation before calibration
TOKEN_CHARS_PER_TOKEN: int = 4
# Safety multiplier applied when comparing raw estimates to thresholds
TOKEN_SAFETY_MARGIN: float = 1.2

# ---------------------------------------------------------------------------
# Observer limits
# ---------------------------------------------------------------------------

# Maximum chars serialised per message section before truncation
OBSERVER_MAX_SECTION_CHARS: int = 6_000
# Maximum chars for tool call payloads
OBSERVER_MAX_TOOL_PAYLOAD_CHARS: int = 3_000
# Max tokens the observer LLM may output
OBSERVER_MAX_OUTPUT_TOKENS: int = 8_000

# ---------------------------------------------------------------------------
# Reflector limits
# ---------------------------------------------------------------------------

REFLECTOR_MAX_OUTPUT_TOKENS: int = 10_000

# ---------------------------------------------------------------------------
# Memory thresholds
# Deliberately low so observer/reflector trigger within a short demo
# conversation.  Raise to ~4000 / 2000 / 1200 for production use.
# ---------------------------------------------------------------------------

OBSERVATION_THRESHOLD_TOKENS: int = 400
REFLECTION_THRESHOLD_TOKENS: int = 400
REFLECTION_TARGET_TOKENS: int = 200

OBSERVER_MODEL: str = "gpt-4.1-mini"
REFLECTOR_MODEL: str = "gpt-4.1-mini"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


DEFAULT_MEMORY_CONFIG: dict = {
    "observation_threshold_tokens": OBSERVATION_THRESHOLD_TOKENS,
    "reflection_threshold_tokens": REFLECTION_THRESHOLD_TOKENS,
    "reflection_target_tokens": REFLECTION_TARGET_TOKENS,
    "observer_model": OBSERVER_MODEL,
    "reflector_model": REFLECTOR_MODEL,
}


def resolve_model_for_provider(model: str) -> str:
    """Resolve a model name for the configured provider.

    For OpenRouter, prepends ``openai/`` when the model string contains no
    slash, mirroring the JS ``resolveModelForProvider`` helper.

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
