# -*- coding: utf-8 -*-

#   characters.py

"""
### Description:
Character-based chunking strategy — splits text into fixed-size windows
with a configurable character overlap between consecutive chunks.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/strategies/characters.js

"""

from typing import Dict, List

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_by_characters(
    text: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """Split *text* into fixed-size character windows with overlap.

    Args:
        text: Full source document text.
        size: Maximum number of characters per chunk.
        overlap: Number of characters to repeat at the start of the next chunk.

    Returns:
        List of chunk dicts ``{"content": str, "metadata": {...}}``.
    """
    chunks: List[str] = []
    start = 0

    while start < len(text):
        chunks.append(text[start: start + size])
        start += size - overlap

    return [
        {
            "content": content,
            "metadata": {
                "strategy": "characters",
                "index": i,
                "chars": len(content),
                "size": size,
                "overlap": overlap,
            },
        }
        for i, content in enumerate(chunks)
    ]
