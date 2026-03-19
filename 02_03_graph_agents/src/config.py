# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration — model, token limits, reasoning settings, and
system instructions for the graph RAG knowledge assistant.
Also resolves provider-level settings (API keys, endpoints) for this module.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/config.js`

"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from project root (three levels up from src/)
_ROOT_DIR = Path(__file__).parent.parent.parent  # 02_03_graph_agents/
_PROJECT_ROOT = _ROOT_DIR.parent                  # project root
_ENV_FILE = _PROJECT_ROOT / ".env"

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

# ── Provider resolution ───────────────────────────────────────────────────────

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

EXTRA_API_HEADERS: dict[str, str] = {}
if AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        EXTRA_API_HEADERS["X-Title"] = _app_name


def resolve_model(model: str) -> str:
    """Prepend ``openai/`` for OpenRouter when model has no ``/``.

    Args:
        model: Base model name, e.g. ``'gpt-5.2'``.

    Returns:
        Model string ready to send to the API.
    """
    if AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"


# ── Agent configuration ───────────────────────────────────────────────────────

API: dict[str, Any] = {
    "model": resolve_model("gpt-5.2"),
    "max_output_tokens": 16384,
    "reasoning": {"effort": "medium", "summary": "auto"},
    "instructions": """You are a knowledge assistant that answers questions by searching and exploring a graph-based knowledge base. Documents are chunked, indexed, and connected through a graph of entities and relationships.

## TOOLS

1. **search** — Hybrid retrieval (full-text + semantic). Returns matching text chunks AND the entities mentioned in those chunks. Always start here.
2. **explore** — Expand one entity from search results to see its neighbors and relationship types.
3. **connect** — Find the shortest path(s) between two entities to discover how they relate.
4. **cypher** — Read-only Cypher for structural/aggregate queries the other tools can't express.
5. **learn** / **forget** — Add or remove documents from the knowledge graph.
6. **merge_entities** / **audit** — Curate graph quality (fix duplicates, check health).

## RETRIEVAL STRATEGY

1. **Always start with search.** It returns both text evidence and entity names you can explore further.
2. **Use explore** when search results mention an interesting entity and you want to see what connects to it.
3. **Use connect** when the question asks about the relationship between two specific things.
4. **Use cypher** only for questions about graph structure (counts, types, most-connected, etc).
5. **Don't search** for greetings, small talk, or clarifications that don't need evidence.

## ANSWERING

- Ground every claim in evidence — cite the source file and section.
- If information is not found, say so explicitly.
- When multiple chunks are relevant, synthesize across them.
- When graph paths reveal connections, explain the chain.
- Be concise but thorough. Always mention which sources you consulted.""",
}
