# -*- coding: utf-8 -*-

#   separators.py

"""
### Description:
Separator-based recursive chunking strategy. Splits text using a hierarchy
of separators (headers → paragraphs → sentences → words), carrying a character
overlap between consecutive chunks. Also annotates each chunk with the
markdown section it belongs to.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/strategies/separators.js

"""

import re
from typing import Dict, List, Optional, Tuple

from ..utils import build_heading_index, find_section

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Separator hierarchy: try to split on the most structural boundaries first,
# falling back to finer-grained splits only when needed.
SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]


def _pick_overlap(text: str, overlap: int, sep: str) -> Tuple[str, bool, bool]:
    """Calculate the overlap text to prepend at the start of the next chunk.

    Takes the last *overlap* characters of *text*, finds the first newline or
    whitespace boundary within that tail, and strips any leading separator
    prefix from the result.

    Args:
        text: The chunk just emitted.
        overlap: Desired overlap length in characters.
        sep: The separator that was used to split this chunk (may be stripped
            from the overlap start).

    Returns:
        Tuple of (overlap_text, was_trimmed, was_dropped) where:
        - ``overlap_text`` is the text to carry over (empty string if nothing),
        - ``was_trimmed`` is True if the overlap is shorter than requested,
        - ``was_dropped`` is True if no usable overlap was found.
    """
    if overlap <= 0:
        return "", False, True

    start = max(0, len(text) - overlap)
    tail = text[start:]

    # Find the first newline; fall back to first whitespace
    idx = tail.find("\n")
    if idx == -1:
        m = re.search(r"\s", tail)
        idx = m.start() if m else -1

    if idx == -1:
        return "", False, True

    overlap_text = text[start + idx + 1:]

    # Strip leading separator so the overlap doesn't start mid-separator
    if sep and overlap_text.startswith(sep):
        overlap_text = overlap_text[len(sep):]

    was_dropped = not overlap_text
    was_trimmed = bool(overlap_text) and len(overlap_text) < overlap
    return overlap_text, was_trimmed, was_dropped


def _split(
    text: str,
    size: int,
    overlap: int,
    separators: List[str],
    stats: Dict[str, int],
) -> List[str]:
    """Recursively split *text* using the first separator that appears in it.

    If the text fits within *size* already, it is returned as-is. Otherwise,
    the function finds the first separator present, splits on it, and
    accumulates chunks. Chunks that are still too large after the primary split
    are recursively re-split with the remaining (finer) separators.

    Args:
        text: Text to split.
        size: Maximum chunk size in characters.
        overlap: Overlap length for consecutive chunks.
        separators: Remaining separator candidates (tried in order).
        stats: Mutable dict tracking ``trimmed`` and ``dropped`` overlap counts.

    Returns:
        List of text chunks, each ≤ *size* characters (best-effort).
    """
    if len(text) <= size:
        return [text]

    # Find the first separator present in the text
    sep = next((s for s in separators if s in text), None)
    if sep is None:
        return [text]  # No separator found — emit as single (oversized) chunk

    parts = text.split(sep)
    chunks: List[str] = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part

        if len(candidate) > size and current:
            # Current accumulator would overflow — emit it and start a new one
            chunks.append(current)
            overlap_text, was_trimmed, was_dropped = _pick_overlap(current, overlap, sep)
            if was_dropped:
                stats["dropped"] += 1
            if was_trimmed:
                stats["trimmed"] += 1
            current = overlap_text + sep + part if overlap_text else part
        else:
            current = candidate

    if current:
        chunks.append(current)

    # Recursively split any chunk still over size using the next separator
    remaining = separators[separators.index(sep) + 1:]
    result: List[str] = []
    for chunk in chunks:
        if len(chunk) > size and remaining:
            result.extend(_split(chunk, size, overlap, remaining, stats))
        else:
            result.append(chunk)
    return result


def chunk_by_separators(
    text: str,
    source: Optional[str] = None,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """Split *text* using the recursive separator hierarchy with overlap.

    Args:
        text: Full source document text.
        source: Optional source file path stored in chunk metadata.
        size: Maximum chunk size in characters.
        overlap: Desired character overlap between consecutive chunks.

    Returns:
        List of chunk dicts ``{"content": str, "metadata": {...}}``.
    """
    stats: Dict[str, int] = {"trimmed": 0, "dropped": 0}
    chunks = _split(text, size, overlap, SEPARATORS, stats)
    headings = build_heading_index(text)
    print(f"[separators] overlap trimmed: {stats['trimmed']}, dropped: {stats['dropped']}")

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
