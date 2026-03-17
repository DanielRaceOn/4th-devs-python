# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Thin LLM wrapper for the OpenAI Responses API used by the chunking strategies
that need LLM enrichment (context and topics strategies).

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/api.js

"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# ── Config (inlined — mirrors root config.js resolution logic) ────────────────

_ROOT_DIR = Path(__file__).parent.parent.parent  # project root
_ROOT_ENV_FILE = _ROOT_DIR / ".env"

_RESPONSES_ENDPOINTS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1/responses",
    "openrouter": "https://openrouter.ai/api/v1/responses",
}
_VALID_PROVIDERS = {"openai", "openrouter"}

if _ROOT_ENV_FILE.exists():
    load_dotenv(_ROOT_ENV_FILE)

_OPENAI_API_KEY: str = (os.environ.get("OPENAI_API_KEY") or "").strip()
_OPENROUTER_API_KEY: str = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
_requested_provider: str = (os.environ.get("AI_PROVIDER") or "").strip().lower()

_has_openai = bool(_OPENAI_API_KEY)
_has_openrouter = bool(_OPENROUTER_API_KEY)

if not _has_openai and not _has_openrouter:
    print("\033[31mError: set OPENAI_API_KEY or OPENROUTER_API_KEY in .env\033[0m", file=sys.stderr)
    sys.exit(1)

_AI_PROVIDER: str = (
    _requested_provider
    if _requested_provider in _VALID_PROVIDERS
    else ("openai" if _has_openai else "openrouter")
)

_AI_API_KEY: str = _OPENAI_API_KEY if _AI_PROVIDER == "openai" else _OPENROUTER_API_KEY
RESPONSES_API_ENDPOINT: str = _RESPONSES_ENDPOINTS[_AI_PROVIDER]

_EXTRA_API_HEADERS: Dict[str, str] = {}
if _AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        _EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        _EXTRA_API_HEADERS["X-Title"] = _app_name


def _resolve_model(model: str) -> str:
    """Prepend ``openai/`` for OpenRouter when the model name has no ``/``."""
    if _AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"


DEFAULT_MODEL: str = _resolve_model("gpt-4.1-mini")


async def chat(
    input_text: str,
    instructions: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Send a single-turn request to the Responses API and return the text reply.

    Args:
        input_text: The user message / document content.
        instructions: Optional system instructions.
        model: Model identifier (provider-resolved).

    Returns:
        Text content of the first message in the response output.

    Raises:
        RuntimeError: If the API returns an error object.
    """
    body: Dict[str, Any] = {"model": model, "input": input_text}
    if instructions:
        body["instructions"] = instructions

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_AI_API_KEY}",
                **_EXTRA_API_HEADERS,
            },
            json=body,
        )

    data: Dict[str, Any] = response.json()

    if data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(msg or str(err))

    # Extract text from the first message item in output
    for item in data.get("output", []):
        if item.get("type") == "message":
            content: List[Dict[str, Any]] = item.get("content", [])
            if content:
                return content[0].get("text", "")

    return ""
