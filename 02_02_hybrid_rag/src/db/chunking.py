# -*- coding: utf-8 -*-

#   chunking.py

"""
### Description:
Separator-based recursive chunking — ported from 02_02_chunking for use in
the hybrid RAG indexer. Shares the same algorithm but omits debug stats
logging (trimmed/dropped counts) to keep indexer output clean.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/db/chunking.js  (ported from 02_02_chunking/src/strategies/separators.js)

"""

import re
from typing import Dict, List, Optional, Tuple

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]


def build_heading_index(text: str) -> List[Dict]:
    """Build a sorted list of heading positions from markdown text.

    Detects markdown ATX headings and plain-text headings (short lines after
    a blank line followed immediately by content).

    Args:
        text: Full source document text.

    Returns:
        List of ``{"position": int, "level": int, "title": str}`` dicts,
        sorted ascending by position.
    """
    headings: List[Dict] = []

    for match in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
        headings.append(
            {"position": match.start(), "level": len(match.group(1)), "title": match.group(2).strip()}
        )

    md_titles = {h["title"] for h in headings}

    for match in re.finditer(r"(?:^|\n\n)([^\n]{1,80})\n(?=[A-Za-z\"'\[(])", text):
        title = match.group(1).strip()
        if not title or title == "Conclusion:" or title in md_titles:
            continue
        offset = 2 if match.group(0).startswith("\n") else 0
        headings.append({"position": match.start() + offset, "level": 1, "title": title})

    headings.sort(key=lambda h: h["position"])
    return headings


def find_section(text: str, chunk_content: str, headings: List[Dict]) -> Optional[str]:
    """Find the section heading that contains a chunk.

    Samples from 40% into the chunk to avoid overlap-related mismatches.

    Args:
        text: Full source document text.
        chunk_content: Text content of the chunk.
        headings: Pre-built heading index from :func:`build_heading_index`.

    Returns:
        Heading string like ``"## Title"`` or ``None``.
    """
    if not headings:
        return None

    mid = int(len(chunk_content) * 0.4)
    sample = chunk_content[mid: mid + 100]
    pos = text.find(sample)
    if pos == -1:
        return None

    current = None
    for h in headings:
        if h["position"] <= pos:
            current = h
        else:
            break

    return "#" * current["level"] + " " + current["title"] if current else None


def _pick_overlap(text: str, overlap: int, sep: str) -> str:
    """Return the overlap text to prepend at the start of the next chunk."""
    if overlap <= 0:
        return ""

    start = max(0, len(text) - overlap)
    tail = text[start:]

    idx = tail.find("\n")
    if idx == -1:
        m = re.search(r"\s", tail)
        idx = m.start() if m else -1

    if idx == -1:
        return ""

    overlap_text = text[start + idx + 1:]
    if sep and overlap_text.startswith(sep):
        overlap_text = overlap_text[len(sep):]

    return overlap_text


def _split(text: str, size: int, overlap: int, separators: List[str]) -> List[str]:
    """Recursively split text using the separator hierarchy."""
    if len(text) <= size:
        return [text]

    sep = next((s for s in separators if s in text), None)
    if sep is None:
        return [text]

    parts = text.split(sep)
    chunks: List[str] = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) > size and current:
            chunks.append(current)
            overlap_text = _pick_overlap(current, overlap, sep)
            current = overlap_text + sep + part if overlap_text else part
        else:
            current = candidate

    if current:
        chunks.append(current)

    remaining = separators[separators.index(sep) + 1:]
    result: List[str] = []
    for chunk in chunks:
        if len(chunk) > size and remaining:
            result.extend(_split(chunk, size, overlap, remaining))
        else:
            result.append(chunk)
    return result


def chunk_by_separators(
    text: str,
    source: Optional[str] = None,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """Split *text* using the recursive separator hierarchy.

    Args:
        text: Full source document text.
        source: Optional source file path stored in chunk metadata.
        size: Maximum chunk size in characters.
        overlap: Desired character overlap between consecutive chunks.

    Returns:
        List of chunk dicts ``{"content": str, "metadata": {...}}``.
    """
    chunks = _split(text, size, overlap, SEPARATORS)
    headings = build_heading_index(text)

    return [
        {
            "content": content,
            "metadata": {
                "strategy": "separators",
                "index": i,
                "chars": len(content),
                "section": find_section(text, content, headings),
                "source": source,
            },
        }
        for i, content in enumerate(chunks)
    ]
