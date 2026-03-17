# -*- coding: utf-8 -*-

#   utils.py

"""
### Description:
Shared heading-detection and section-lookup utilities used by the separator,
context, and topics chunking strategies.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/utils.js

"""

import re
from typing import Dict, List, Optional


def build_heading_index(text: str) -> List[Dict]:
    """Build a sorted list of heading positions from markdown text.

    Detects two kinds of headings:
    1. Markdown ATX headings (``# Title``, ``## Title``, etc.)
    2. Plain-text headings: short standalone lines (≤80 chars) that appear
       after a blank line and are immediately followed by content.

    Args:
        text: Full source document text.

    Returns:
        List of dicts ``{"position": int, "level": int, "title": str}``,
        sorted ascending by position.
    """
    headings: List[Dict] = []

    # 1. Markdown # headings
    for match in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
        headings.append(
            {
                "position": match.start(),
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
            }
        )

    # 2. Plain-text headings: short line after blank line, followed immediately
    #    by non-blank content (single \n, not \n\n).
    md_titles = {h["title"] for h in headings}

    for match in re.finditer(r"(?:^|\n\n)([^\n]{1,80})\n(?=[A-Za-z\"'\[(])", text):
        title = match.group(1).strip()
        if not title or title == "Conclusion:" or title in md_titles:
            continue
        # Offset past the leading \n\n if present
        offset = 2 if match.group(0).startswith("\n") else 0
        headings.append({"position": match.start() + offset, "level": 1, "title": title})

    headings.sort(key=lambda h: h["position"])
    return headings


def find_section(
    text: str, chunk_content: str, headings: List[Dict]
) -> Optional[str]:
    """Find which heading a chunk falls under by sampling from ~40% into the chunk.

    Sampling from the middle (rather than the start) avoids false matches caused
    by overlap text that was carried over from the previous chunk.

    Args:
        text: Full source document text.
        chunk_content: Text content of the chunk to locate.
        headings: Pre-built heading index from :func:`build_heading_index`.

    Returns:
        Heading string like ``"## Section Title"``, or ``None`` if not found.
    """
    if not headings:
        return None

    # Sample from 40% into the chunk to avoid overlap artifacts
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

    if current is None:
        return None
    return "#" * current["level"] + " " + current["title"]
