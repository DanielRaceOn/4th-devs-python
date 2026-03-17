# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Agent configuration — model, token limits, reasoning settings, and system
instructions for the hybrid RAG knowledge assistant.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/config.js

"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

_ROOT_DIR = Path(__file__).parent.parent.parent  # project root
_ROOT_ENV_FILE = _ROOT_DIR / ".env"

if _ROOT_ENV_FILE.exists():
    load_dotenv(_ROOT_ENV_FILE)

_OPENAI_API_KEY: str = (os.environ.get("OPENAI_API_KEY") or "").strip()
_OPENROUTER_API_KEY: str = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
_requested_provider: str = (os.environ.get("AI_PROVIDER") or "").strip().lower()

AI_PROVIDER: str = (
    _requested_provider
    if _requested_provider in ("openai", "openrouter")
    else ("openai" if _OPENAI_API_KEY else "openrouter")
)

AI_API_KEY: str = _OPENAI_API_KEY if AI_PROVIDER == "openai" else _OPENROUTER_API_KEY

RESPONSES_API_ENDPOINT: str = (
    "https://api.openai.com/v1/responses"
    if AI_PROVIDER == "openai"
    else "https://openrouter.ai/api/v1/responses"
)

EMBEDDINGS_API_ENDPOINT: str = (
    "https://api.openai.com/v1/embeddings"
    if AI_PROVIDER == "openai"
    else "https://openrouter.ai/api/v1/embeddings"
)

EXTRA_API_HEADERS: Dict[str, str] = {}
if AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        EXTRA_API_HEADERS["X-Title"] = _app_name


def resolve_model(model: str) -> str:
    """Prepend ``openai/`` for OpenRouter when model has no ``/``."""
    if AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"


# ── Agent configuration ───────────────────────────────────────────────────────

API: Dict[str, Any] = {
    "model": resolve_model("gpt-4.1"),
    "max_output_tokens": 16384,
    "reasoning": {"effort": "medium", "summary": "auto"},
    "instructions": """You are a knowledge assistant that answers questions by searching an indexed document database. You have a single tool — **search** — that performs hybrid retrieval (full-text BM25 + semantic vector similarity) over pre-indexed documents.

## WHEN TO SEARCH

- Use the search tool ONLY when the user asks a question or requests information that could be in the documents.
- Do NOT search for greetings, small talk, or follow-up clarifications that don't need document evidence.
- When in doubt whether to search, prefer searching.

## HOW TO SEARCH

- Start with a broad query, then refine with more specific terms based on what you find.
- Try multiple angles: synonyms, related concepts, specific names, and technical terms.
- If initial results are insufficient, search again with different keywords derived from partial findings.
- Stop searching only when you have enough evidence to answer confidently, or when repeated searches yield no new information.

## RULES

- Ground every claim in search results — cite the source file and section.
- If the information is not found, say so explicitly.
- When multiple chunks are relevant, synthesize across them.
- Be concise but thorough.
- Always mention which source files you consulted.""",
}
