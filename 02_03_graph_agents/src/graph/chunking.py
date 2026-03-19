# -*- coding: utf-8 -*-

#   chunking.py

"""
### Description:
Separator-based (recursive) chunking. Splits text using a hierarchy of
separators: Markdown headers → paragraphs → sentences → words.
Identical logic to 02_02_hybrid_rag — carried over as-is.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/chunking.js`

"""

import re

CHUNK_SIZE = 4000
CHUNK_OVERLAP = 500
SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]


# ── Heading index utilities ───────────────────────────────────────────────────

def build_heading_index(text: str) -> list[dict]:
    """Build a sorted list of heading positions found in ``text``.

    Detects both Markdown ATX headings (``# Title``) and plain-text titles
    (short lines followed by prose).

    Args:
        text: Full document text.

    Returns:
        List of ``{position, level, title}`` dicts, sorted by position.
    """
    headings: list[dict] = []

    # Markdown headings: ## Title
    for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
        headings.append({
            "position": m.start(),
            "level": len(m.group(1)),
            "title": m.group(2).strip(),
        })

    md_titles = {h["title"] for h in headings}

    # Plain-text title heuristic: short line followed by prose
    for m in re.finditer(r"(?:^|\n\n)([^\n]{1,80})\n(?=[A-Za-z\"'\[(])", text):
        title = m.group(1).strip()
        if not title or title == "Conclusion:" or title in md_titles:
            continue
        offset = 2 if m.group(0).startswith("\n") else 0
        headings.append({"position": m.start() + offset, "level": 1, "title": title})

    return sorted(headings, key=lambda h: h["position"])


def find_section(text: str, chunk_content: str, headings: list[dict]) -> str | None:
    """Find the heading that the given chunk falls under.

    Args:
        text: Full document text.
        chunk_content: Content of a single chunk.
        headings: Heading index from ``build_heading_index``.

    Returns:
        Heading string like ``"## Section Title"``, or ``None``.
    """
    if not headings:
        return None

    # Sample from ~40% into the chunk to avoid overlap bleed-over
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
    return f"{'#' * current['level']} {current['title']}"


# ── Overlap helper ────────────────────────────────────────────────────────────

def _pick_overlap(text: str, overlap: int, sep: str) -> str:
    """Extract overlap text from the tail of ``text``.

    Trims to the nearest newline or whitespace boundary, and strips any
    leading separator so chunks don't start with a raw separator.

    Args:
        text: The completed chunk text.
        overlap: Target overlap length in characters.
        sep: The separator used at this recursion level.

    Returns:
        Overlap string (may be empty if no suitable boundary found).
    """
    if overlap <= 0:
        return ""

    start = max(0, len(text) - overlap)
    tail = text[start:]

    idx = tail.find("\n")
    if idx == -1:
        # Fall back to any whitespace boundary
        m = re.search(r"\s", tail)
        idx = m.start() if m else -1
    if idx == -1:
        return ""

    overlap_text = text[start + idx + 1:]
    if sep and overlap_text.startswith(sep):
        overlap_text = overlap_text[len(sep):]
    return overlap_text


# ── Recursive split ───────────────────────────────────────────────────────────

def _split(text: str, size: int, overlap: int, separators: list[str]) -> list[str]:
    """Recursively split ``text`` into chunks of at most ``size`` characters.

    Tries each separator in order, splitting at the first one present.
    Remaining separators are used for sub-splits of oversized chunks.

    Args:
        text: Text to split.
        size: Maximum chunk size in characters.
        overlap: Overlap length carried from one chunk to the next.
        separators: Ordered list of separator strings to try.

    Returns:
        List of chunk strings.
    """
    if len(text) <= size:
        return [text]

    sep = next((s for s in separators if s in text), None)
    if sep is None:
        return [text]

    parts = text.split(sep)
    chunks: list[str] = []
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
    result: list[str] = []
    for c in chunks:
        if len(c) > size and remaining:
            result.extend(_split(c, size, overlap, remaining))
        else:
            result.append(c)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_by_separators(
    text: str,
    *,
    source: str | None = None,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split ``text`` into chunks with metadata.

    Args:
        text: Full document text to chunk.
        source: Source label to embed in each chunk's metadata.
        size: Target maximum chunk size in characters.
        overlap: Overlap between consecutive chunks.

    Returns:
        List of ``{content, metadata}`` dicts where ``metadata`` contains
        ``strategy``, ``index``, ``chars``, ``section``, and ``source``.
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
