# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions for the hybrid RAG agent. Exposes a single ``search``
tool that performs hybrid retrieval (FTS5 BM25 + vector similarity) over the
indexed document database.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/agent/tools.js

"""

import json
import sqlite3
from typing import Any, Callable, Dict, List

from ..db.search import hybrid_search
from ..helpers import logger as log

SEARCH_TOOL: Dict[str, Any] = {
    "type": "function",
    "name": "search",
    "description": (
        "Search the indexed knowledge base using hybrid search "
        "(full-text BM25 + semantic vector similarity). "
        "Returns the most relevant document chunks with content, source file, "
        "and section heading. "
        "Provide BOTH a keyword query for full-text search AND a natural language "
        "query for semantic search."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": (
                    "Keywords for full-text search (BM25) — specific terms, names, "
                    "and phrases that should appear in the text"
                ),
            },
            "semantic": {
                "type": "string",
                "description": (
                    "Natural language query for semantic/vector search — a question "
                    "or description of the concept you're looking for"
                ),
            },
            "limit": {
                "type": "number",
                "description": "Maximum number of results to return (default 5, max 20)",
            },
        },
        "required": ["keywords", "semantic"],
    },
    "strict": False,
}


def create_tools(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Create the tool interface consumed by the agent loop.

    Args:
        conn: Open database connection.

    Returns:
        Dict with ``definitions`` (list of tool schemas) and ``handle``
        (async callable dispatching tool calls by name).
    """

    async def _search_handler(keywords: str, semantic: str, limit: int = 5) -> str:
        results = await hybrid_search(
            conn, {"keywords": keywords, "semantic": semantic}, min(limit, 20)
        )
        return json.dumps(
            [{"source": r["source"], "section": r["section"], "content": r["content"]} for r in results],
            ensure_ascii=False,
        )

    _handlers: Dict[str, Callable] = {"search": _search_handler}

    async def handle(name: str, args: Dict[str, Any]) -> str:
        handler = _handlers.get(name)
        if not handler:
            raise RuntimeError(f"Unknown tool: {name}")

        log.tool(name, args)

        try:
            result = await handler(**args)
            log.tool_result(name, True, result)
            return result
        except Exception as exc:  # noqa: BLE001
            output = json.dumps({"error": str(exc)})
            log.tool_result(name, False, str(exc))
            return output

    return {
        "definitions": [SEARCH_TOOL],
        "handle": handle,
    }
