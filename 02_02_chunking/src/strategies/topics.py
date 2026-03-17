# -*- coding: utf-8 -*-

#   topics.py

"""
### Description:
Topic-based (AI-driven) chunking strategy. Sends the entire document to the
LLM in a single call and asks it to identify logical topic boundaries,
returning a JSON array of {topic, content} objects. Annotates each chunk with
section metadata from the heading index.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/strategies/topics.js

"""

import json
import re
from typing import Dict, List, Optional

from ..api import chat
from ..utils import build_heading_index, find_section

_TOPICS_INSTRUCTIONS = """You are a document chunking expert. Break the provided document into logical topic-based chunks.

Rules:
- Each chunk must contain ONE coherent topic or idea
- Preserve the original text — do NOT summarise or rewrite
- Return a JSON array of objects: [{ "topic": "short topic label", "content": "original text for this topic" }]
- Return ONLY the JSON array, no markdown fences or explanation"""


async def chunk_by_topics(
    text: str,
    source: Optional[str] = None,
) -> List[Dict]:
    """Send the full document to the LLM and return topic-segmented chunks.

    The LLM receives the entire document and is instructed to return a JSON
    array. If the raw response is wrapped in markdown code fences, they are
    stripped before parsing.

    Args:
        text: Full source document text.
        source: Optional source file path stored in chunk metadata.

    Returns:
        List of chunk dicts ``{"content": str, "metadata": {...}}``.

    Raises:
        json.JSONDecodeError: If the LLM response cannot be parsed as JSON
            even after stripping markdown fences.
    """
    raw = await chat(text, _TOPICS_INSTRUCTIONS)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Strip markdown code fences (```json ... ```) if present
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        parsed = json.loads(cleaned)

    headings = build_heading_index(text)

    return [
        {
            "content": item["content"],
            "metadata": {
                "strategy": "topics",
                "index": i,
                "topic": item["topic"],
                "chars": len(item["content"]),
                "section": find_section(text, item["content"], headings),
                "source": source,
            },
        }
        for i, item in enumerate(parsed)
    ]
